import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, SafeAreaView, ActivityIndicator } from 'react-native';
import { AudioSession, LiveKitRoom, useRoomContext, useVoiceAssistant } from '@livekit/react-native';

// UPDATE THIS: Use 10.0.2.2 for Android Emulator or your PC's local IP (e.g., 192.168.1.50) for a physical phone
const BACKEND_URL = 'http://192.168.0.105:8000';
const LIVEKIT_URL = 'ws://192.168.0.105:7880';

export default function App() {
  const [token, setToken] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  // Initialize Audio Session for high-quality voice communication
  useEffect(() => {
    const startAudioSession = async () => {
      await AudioSession.startAudioSession();
    };
    startAudioSession();
    return () => {
      AudioSession.stopAudioSession();
    };
  }, []);

  const fetchToken = async () => {
    try {
      setConnecting(true);
      const res = await fetch(`${BACKEND_URL}/api/v1/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          room_name: 'osmiumcore-default',
          participant_identity: 'mobile-user',
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      setToken(data.token);
    } catch (err) {
      console.error('Failed to get token:', err);
      setConnecting(false);
    }
  };

  const handleDisconnect = () => {
    setToken(null);
    setIsConnected(false);
    setConnecting(false);
  };

  if (!token) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.card}>
          <Text style={styles.title}>OsmiumCore</Text>
          <Text style={styles.subtitle}>Voice Assistant</Text>
          <TouchableOpacity 
            style={styles.button} 
            onPress={fetchToken}
            disabled={connecting}
          >
            {connecting ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.buttonText}>Connect Voice Assistant</Text>
            )}
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={LIVEKIT_URL}
      token={token}
      connect={true}
      audio={true}
      video={false}
      onConnected={() => {
        setConnecting(false);
        setIsConnected(true);
      }}
      onDisconnected={handleDisconnect}
      style={styles.container}
    >
      <AssistantUI onDisconnect={handleDisconnect} />
    </LiveKitRoom>
  );
}

function AssistantUI({ onDisconnect }) {
  const { state, agent } = useVoiceAssistant();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>OsmiumCore</Text>
        <Text style={styles.statusText}>
          Status: <Text style={styles.bold}>{state || 'Connecting...'}</Text>
        </Text>

        <TouchableOpacity style={[styles.button, styles.disconnectButton]} onPress={onDisconnect}>
          <Text style={styles.buttonText}>Disconnect</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F0F11',
    alignItems: 'center',
    justifyContent: 'center',
  },
  card: {
    width: '85%',
    backgroundColor: '#1A1A1E',
    padding: 24,
    borderRadius: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2A2A30',
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#888892',
    marginBottom: 32,
  },
  statusText: {
    fontSize: 16,
    color: '#CCCCCC',
    marginVertical: 24,
  },
  bold: {
    fontWeight: 'bold',
    color: '#4F46E5',
  },
  button: {
    backgroundColor: '#4F46E5',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 8,
    width: '100%',
    alignItems: 'center',
  },
  disconnectButton: {
    backgroundColor: '#DC2626',
    marginTop: 16,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '600',
  },
});