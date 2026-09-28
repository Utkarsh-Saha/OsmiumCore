import React, { useState, useRef, useEffect, useCallback } from "react";
import { sendTextMessage, transcribeAudioFile } from "../services/api";

interface MessageItem {
  id: string;
  type: "text" | "voice";
  sender: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

interface TextChatProps {
  userId: string;
  sessionId?: string;
}

export const TextChat: React.FC<TextChatProps> = ({ userId, sessionId }) => {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [autoSpeak, setAutoSpeak] = useState<boolean>(true);
  const [speakingId, setSpeakingId] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const formatTime = () =>
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSubmitting]);

  // Text-To-Speech Synthesis helper
  const speakText = useCallback((text: string, msgId?: string) => {
    if (!("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();

    // Remove markdown symbols for cleaner speech
    const cleanText = text
      .replace(/[#*_`~>-]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    // Pick natural English voice if available
    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(
      (v) =>
        v.lang.startsWith("en") &&
        (v.name.includes("Natural") ||
          v.name.includes("Google") ||
          v.name.includes("Samantha") ||
          v.name.includes("David") ||
          v.name.includes("Jenny"))
    ) || voices.find((v) => v.lang.startsWith("en"));

    if (naturalVoice) {
      utterance.voice = naturalVoice;
    }

    if (msgId) setSpeakingId(msgId);

    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = () => setSpeakingId(null);

    window.speechSynthesis.speak(utterance);
  }, []);

  const stopSpeaking = () => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setSpeakingId(null);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const text = (typeof textToSend === "string" ? textToSend : inputText).trim();
    if (!text || isSubmitting) return;

    const userMsg: MessageItem = {
      id: "user-" + Date.now(),
      type: textToSend ? "voice" : "text",
      sender: "user",
      content: text,
      timestamp: formatTime(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputText("");
    setIsSubmitting(true);
    setStatusText("Osmium is thinking...");

    try {
      const res = await sendTextMessage(userId, text, sessionId);
      if (res.reply) {
        const asstMsgId = "asst-" + Date.now();
        const asstMsg: MessageItem = {
          id: asstMsgId,
          type: "text",
          sender: "assistant",
          content: res.reply,
          timestamp: formatTime(),
        };
        setMessages((prev) => [...prev, asstMsg]);

        // Speak the reply aloud if Auto-Speak is enabled
        if (autoSpeak) {
          speakText(res.reply, asstMsgId);
        }
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: "err-" + Date.now(),
          type: "text",
          sender: "system",
          content: `Error: ${err.message}`,
          timestamp: formatTime(),
        },
      ]);
    } finally {
      setIsSubmitting(false);
      setStatusText("");
    }
  };

  const handleAudioUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsSubmitting(true);
    setStatusText("Transcribing audio file with Whisper...");

    try {
      const res = await transcribeAudioFile(userId, file, sessionId);
      if (res.text && res.text.trim()) {
        setStatusText("");
        setIsSubmitting(false);
        // Automatically ask the assistant about the transcribed audio query
        await handleSendMessage(res.text.trim());
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: "audio-" + Date.now(),
            type: "voice",
            sender: "system",
            content: "No speech detected in the audio file.",
            timestamp: formatTime(),
          },
        ]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: "err-" + Date.now(),
          type: "text",
          sender: "system",
          content: `Transcription error: ${err.message}`,
          timestamp: formatTime(),
        },
      ]);
    } finally {
      setIsSubmitting(false);
      setStatusText("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const startLiveRecording = async () => {
    stopSpeaking();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        stream.getTracks().forEach((track) => track.stop());

        setIsSubmitting(true);
        setStatusText("Transcribing recorded voice with Whisper...");
        try {
          const res = await transcribeAudioFile(userId, audioBlob, sessionId);
          if (res.text && res.text.trim()) {
            setStatusText("");
            setIsSubmitting(false);
            // Automatically ask the assistant about the transcribed speech
            await handleSendMessage(res.text.trim());
          } else {
            setMessages((prev) => [
              ...prev,
              {
                id: "stt-empty-" + Date.now(),
                type: "voice",
                sender: "system",
                content: "No speech detected in your microphone recording.",
                timestamp: formatTime(),
              },
            ]);
          }
        } catch (err: any) {
          setMessages((prev) => [
            ...prev,
            {
              id: "err-" + Date.now(),
              type: "text",
              sender: "system",
              content: `Voice error: ${err.message}`,
              timestamp: formatTime(),
            },
          ]);
        } finally {
          setIsSubmitting(false);
          setStatusText("");
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      setStatusText("Recording microphone audio (speak now)...");
    } catch (err: any) {
      console.error("Microphone access error:", err);
      alert(`Could not access microphone: ${err.message}`);
    }
  };

  const stopLiveRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="header-left">
          <h3 className="chat-title">Text & Voice Chat</h3>
          <span className="chat-user-badge">User: {userId}</span>
        </div>
        <div className="header-right">
          <button
            type="button"
            className={`btn-tts-toggle ${autoSpeak ? "tts-on" : "tts-off"}`}
            onClick={() => {
              if (autoSpeak) stopSpeaking();
              setAutoSpeak(!autoSpeak);
            }}
            title={autoSpeak ? "Auto-Voice Speech is ON (Click to Mute)" : "Auto-Voice Speech is Muted (Click to Enable)"}
          >
            {autoSpeak ? "🔊 Voice ON" : "🔇 Voice OFF"}
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <p className="empty-title">Ready for Conversation</p>
            <span className="empty-subtitle">
              Type a question below, speak via mic, or upload an audio file to chat with Osmium.
            </span>
          </div>
        ) : (
          messages.map((m) => {
            const isUser = m.sender === "user";
            const isAsst = m.sender === "assistant";
            const bubbleClass = isUser
              ? "bubble-user"
              : isAsst
              ? "bubble-assistant"
              : "bubble-system";

            return (
              <div key={m.id} className={`chat-bubble ${bubbleClass}`}>
                <div className="bubble-header">
                  <span className="bubble-tag">
                    {isUser
                      ? m.type === "voice"
                        ? "🎙️ You (Voice)"
                        : "👤 You"
                      : isAsst
                      ? "⚡ Osmium Assistant"
                      : "ℹ️ System"}
                  </span>
                  <div className="bubble-actions">
                    {isAsst && (
                      <button
                        type="button"
                        className="btn-replay-speech"
                        onClick={() => {
                          if (speakingId === m.id) {
                            stopSpeaking();
                          } else {
                            speakText(m.content, m.id);
                          }
                        }}
                        title={speakingId === m.id ? "Stop Speaking" : "Play Speech"}
                      >
                        {speakingId === m.id ? "⏹️ Stop" : "🔊 Speak"}
                      </button>
                    )}
                    <span className="bubble-time">{m.timestamp}</span>
                  </div>
                </div>
                <p className="bubble-text">{m.content}</p>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {statusText && (
        <div className="recording-status">
          <span className="pulse-dot"></span>
          {statusText}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
        className="chat-input-form"
      >
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ask OsmiumCore anything..."
          className="chat-text-input"
          disabled={isSubmitting || isRecording}
        />

        <button
          type="submit"
          className="chat-btn chat-btn-send"
          disabled={!inputText.trim() || isSubmitting || isRecording}
          title="Send message"
        >
          Send
        </button>

        {!isRecording ? (
          <button
            type="button"
            onClick={startLiveRecording}
            className="chat-btn chat-btn-mic"
            disabled={isSubmitting}
            title="Record voice & send"
          >
            🎙️ Mic
          </button>
        ) : (
          <button
            type="button"
            onClick={stopLiveRecording}
            className="chat-btn chat-btn-stop"
            title="Stop recording & send"
          >
            ⏹️ Stop
          </button>
        )}

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="chat-btn chat-btn-upload"
          disabled={isSubmitting || isRecording}
          title="Upload audio file (.wav, .mp3, .webm)"
        >
          📁 Audio
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          style={{ display: "none" }}
          onChange={handleAudioUpload}
        />
      </form>
    </div>
  );
};
