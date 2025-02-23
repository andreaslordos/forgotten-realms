// src/App.js
import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';

function App() {
  const [phase, setPhase] = useState('login'); // 'login' or 'game'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [messages, setMessages] = useState([]);
  const [command, setCommand] = useState('');
  
  const socketRef = useRef(null);

  useEffect(() => {
    // Connect to the backend Socket.IO server.
    socketRef.current = io('http://localhost:8888');

    socketRef.current.on('connect', () => {
      console.log('Connected to backend.');
    });

    socketRef.current.on('loginSuccess', () => {
      setPhase('game');
    });

    socketRef.current.on('loginFailure', (error) => {
      alert(`Login failed: ${error}`);
    });

    socketRef.current.on('message', (msg) => {
      setMessages(prev => [...prev, msg]);
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  const handleLogin = (e) => {
    e.preventDefault();
    socketRef.current.emit('login', { username, password });
  };

  const handleCommandSubmit = (e) => {
    e.preventDefault();
    socketRef.current.emit('command', command);
    setCommand('');
  };

  if (phase === 'login') {
    return (
      <div style={{ padding: '2rem' }}>
        <h1>AI MUD</h1>
        <form onSubmit={handleLogin}>
          <div>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit">Login</button>
        </form>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h1>AI MUD Game</h1>
      <div
        style={{
          border: '1px solid #ccc',
          padding: '1rem',
          height: '300px',
          overflowY: 'scroll',
          backgroundColor: '#f9f9f9',
          marginBottom: '1rem',
          whiteSpace: 'pre-wrap'
        }}
      >
        {messages.map((msg, index) => (
          <div key={index}>{msg}</div>
        ))}
      </div>
      <form onSubmit={handleCommandSubmit}>
        <input
          type="text"
          placeholder="Enter command..."
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          style={{ width: '80%', padding: '0.5rem' }}
          required
        />
        <button type="submit" style={{ padding: '0.5rem' }}>Send</button>
      </form>
    </div>
  );
}

export default App;
