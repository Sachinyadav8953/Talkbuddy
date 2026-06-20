import { useState, useRef, useEffect, useCallback } from 'react';

export interface UseAudioRecorderType {
  isRecording: boolean;
  recordingTime: number;
  audioLevel: number;
  startRecording: (onDataAvailable: (data: Blob) => void) => Promise<void>;
  stopRecording: () => void;
  audioBlob: Blob | null;
}

export const useAudioRecorder = (): UseAudioRecorderType => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  
  // Web Audio API refs for visualizer
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Periodically compute volume level
  const analyzeVolume = useCallback(() => {
    if (!analyserRef.current) return;
    
    const array = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(array);
    
    // Calculate average volume
    let sum = 0;
    for (let i = 0; i < array.length; i++) {
      sum += array[i];
    }
    const average = sum / array.length;
    // Map average (0-255) to level (0-100)
    setAudioLevel(Math.min(100, Math.round((average / 128) * 100)));
    
    animationFrameRef.current = requestAnimationFrame(analyzeVolume);
  }, []);

  const startRecording = async (onDataAvailable: (data: Blob) => void) => {
    chunksRef.current = [];
    setAudioBlob(null);
    setRecordingTime(0);
    setAudioLevel(0);

    try {
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Set up Web Audio API for volume levels
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      
      // Start volume analysis
      analyzeVolume();

      // Configure MediaRecorder
      // Choose webm/opus on Chrome/Firefox, fallback to default if not supported
      let mimeType = 'audio/webm';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = ''; // Let browser choose default
      }
      
      const options = mimeType ? { mimeType } : undefined;
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
          // Callback to stream audio chunk via WebSocket
          onDataAvailable(event.data);
        }
      };

      // Start recording, triggers ondataavailable every 250ms
      mediaRecorder.start(250);
      setIsRecording(true);

      // Start timer
      timerRef.current = window.setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);

    } catch (err) {
      console.error('Failed to start audio recording:', err);
      throw err;
    }
  };

  const stopRecording = () => {
    if (!mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') return;

    // Stop recorder
    mediaRecorderRef.current.stop();
    setIsRecording(false);

    // Stop timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    // Stop volume animation
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    // Close AudioContext
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
    }

    // Stop all audio stream tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    // Assemble final audio blob
    mediaRecorderRef.current.onstop = () => {
      const finalBlob = new Blob(chunksRef.current, { type: mediaRecorderRef.current?.mimeType || 'audio/webm' });
      setAudioBlob(finalBlob);
    };
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') audioContextRef.current.close();
      if (streamRef.current) streamRef.current.getTracks().forEach((track) => track.stop());
    };
  }, []);

  return {
    isRecording,
    recordingTime,
    audioLevel,
    startRecording,
    stopRecording,
    audioBlob
  };
};
