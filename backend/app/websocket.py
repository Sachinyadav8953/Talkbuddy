import os
import uuid
import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.auth import get_current_user_websocket
from app import models
from app.services.stt_service import stt_service
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.config import settings

logger = logging.getLogger("talkbuddy.websocket")
router = APIRouter()


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: int,
    token: str = Query(...)
):
    # Establish connection
    await websocket.accept()
    logger.info(f"WebSocket connection request for session {session_id}")

    db: Session = SessionLocal()
    user = get_current_user_websocket(token, db)

    if not user:
        logger.warning("WebSocket authentication failed. Rejecting connection.")
        await websocket.close(code=4008)  # Policy Violation
        db.close()
        return

    # Verify session ownership
    chat_session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == user.id
    ).first()

    if not chat_session:
        logger.warning(f"Session {session_id} not found or doesn't belong to user {user.username}")
        await websocket.close(code=4004)  # Not Found
        db.close()
        return

    logger.info(f"WebSocket client connected: {user.username} for session {session_id}")

    # Track the temporary audio file — use a unique path per recording to avoid overwrites
    temp_audio_dir = settings.TEMP_AUDIO_DIR
    os.makedirs(temp_audio_dir, exist_ok=True)
    temp_audio_path = os.path.join(temp_audio_dir, f"stream_{session_id}_{uuid.uuid4().hex}.webm")
    audio_file = None

    try:
        while True:
            # Receive data (can be binary or text)
            message = await websocket.receive()

            if "bytes" in message:
                # Binary message: stream of audio bytes
                audio_bytes = message["bytes"]
                if audio_file is None:
                    # Open a new audio file for writing
                    audio_file = open(temp_audio_path, "wb")
                audio_file.write(audio_bytes)
                audio_file.flush()

            elif "text" in message:
                # Text message: control command
                try:
                    data = json.loads(message["text"])
                    event = data.get("event")

                    if event == "start_audio":
                        logger.info("Received start_audio event. Resetting buffer.")
                        # Clean up existing file if any
                        if audio_file:
                            audio_file.close()
                            audio_file = None
                        if os.path.exists(temp_audio_path):
                            os.remove(temp_audio_path)

                        # Generate fresh unique path for this recording
                        temp_audio_path = os.path.join(
                            temp_audio_dir,
                            f"stream_{session_id}_{uuid.uuid4().hex}.webm"
                        )
                        # Re-open fresh file
                        audio_file = open(temp_audio_path, "wb")

                    elif event == "stop_audio":
                        logger.info("Received stop_audio event. Processing audio...")

                        if audio_file:
                            audio_file.close()
                            audio_file = None

                        if not os.path.exists(temp_audio_path) or os.path.getsize(temp_audio_path) == 0:
                            await websocket.send_text(json.dumps({
                                "event": "error",
                                "message": "No audio received."
                            }))
                            continue

                        # Run blocking AI services on a thread pool to avoid blocking the event loop
                        loop = asyncio.get_running_loop()

                        try:
                            # 1. Speech to Text (with timeout to prevent hanging)
                            await websocket.send_text(json.dumps({"event": "status", "message": "Transcribing..."}))
                            try:
                                user_transcription = await asyncio.wait_for(
                                    loop.run_in_executor(
                                        None, stt_service.transcribe, temp_audio_path
                                    ),
                                    timeout=120  # 2-minute timeout for STT
                                )
                            except asyncio.TimeoutError:
                                logger.error("STT transcription timed out after 120 seconds")
                                await websocket.send_text(json.dumps({
                                    "event": "error",
                                    "message": "Speech transcription timed out. The Whisper model may still be loading. Please try again in a moment."
                                }))
                                continue

                            # Clean up temp file
                            if os.path.exists(temp_audio_path):
                                os.remove(temp_audio_path)

                            if not user_transcription or len(user_transcription.strip()) < 2:
                                await websocket.send_text(json.dumps({
                                    "event": "error",
                                    "message": "I couldn't hear you clearly. Please try speaking again."
                                }))
                                continue

                            # 2. Get conversation history
                            history_msgs = db.query(models.Message).filter(
                                models.Message.session_id == session_id
                            ).order_by(models.Message.created_at.asc()).all()

                            formatted_history = []
                            for m in history_msgs:
                                if m.original_text:
                                    formatted_history.append({"role": "user", "content": m.original_text})
                                formatted_history.append({"role": "assistant", "content": m.response_text})

                            # Keep only last 10 messages for context window stability
                            formatted_history = formatted_history[-10:]

                            # 3. Query LLM (blocking -> run in executor, with timeout)
                            await websocket.send_text(json.dumps({"event": "status", "message": "Thinking..."}))
                            try:
                                coach_response = await asyncio.wait_for(
                                    loop.run_in_executor(
                                        None,
                                        llm_service.query_coach,
                                        user_transcription,
                                        formatted_history,
                                        chat_session.mode
                                    ),
                                    timeout=130  # Slightly above the 120s requests timeout
                                )
                            except asyncio.TimeoutError:
                                logger.error("LLM query timed out after 130 seconds")
                                await websocket.send_text(json.dumps({
                                    "event": "error",
                                    "message": "AI coaching response timed out. Please check your LLM API key and model settings."
                                }))
                                continue

                            # 4. Text-to-Speech using Piper (blocking -> run in executor)
                            await websocket.send_text(json.dumps({"event": "status", "message": "Speaking..."}))
                            tts_text = f"{coach_response['ai_reply']} {coach_response['follow_up_question']}"
                            audio_response_bytes = await loop.run_in_executor(
                                None, tts_service.generate_speech, tts_text
                            )

                            # 5. Save session logs to database
                            db_message = models.Message(
                                session_id=session_id,
                                role="user",
                                original_text=user_transcription,
                                corrected_text=coach_response["correction"],
                                explanation=coach_response["grammar_notes"],
                                suggestions=coach_response["vocabulary_improvement"],
                                response_text=f"{coach_response['ai_reply']} {coach_response['follow_up_question']}",
                                grammar_score=coach_response["scores"]["grammar"],
                                vocabulary_score=coach_response["scores"]["vocabulary"],
                                fluency_score=coach_response["scores"]["fluency"]
                            )
                            db.add(db_message)
                            db.commit()
                            db.refresh(db_message)

                            # 6. Send results back to Client
                            # A. Send JSON feedback
                            await websocket.send_text(json.dumps({
                                "event": "feedback",
                                "message_id": db_message.id,
                                "original_text": user_transcription,
                                "corrected_text": coach_response["correction"],
                                "explanation": coach_response["grammar_notes"],
                                "suggestions": coach_response["vocabulary_improvement"],
                                "response_text": coach_response["ai_reply"],
                                "follow_up_question": coach_response["follow_up_question"],
                                "scores": coach_response["scores"]
                            }))

                            # B. Send Binary Audio Response
                            if audio_response_bytes:
                                await websocket.send_bytes(audio_response_bytes)
                            else:
                                await websocket.send_text(json.dumps({
                                    "event": "error",
                                    "message": "Audio synthesis failed. You can read my text feedback below."
                                }))

                        except Exception as pipeline_err:
                            logger.error(f"Pipeline error during stop_audio: {str(pipeline_err)}", exc_info=True)
                            try:
                                await websocket.send_text(json.dumps({
                                    "event": "error",
                                    "message": f"Processing error: {str(pipeline_err)}"
                                }))
                            except Exception:
                                pass

                except json.JSONDecodeError:
                    logger.error("Failed to decode text message as JSON")
                except Exception as e:
                    logger.error(f"Error processing WS event: {str(e)}", exc_info=True)
                    try:
                        await websocket.send_text(json.dumps({
                            "event": "error",
                            "message": f"An error occurred: {str(e)}"
                        }))
                    except Exception:
                        pass  # WebSocket may already be closed

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {user.username}")
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {str(e)}", exc_info=True)
    finally:
        db.close()
        if audio_file:
            try:
                audio_file.close()
            except Exception:
                pass
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception:
                pass
