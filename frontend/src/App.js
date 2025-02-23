import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';

function App() {
  // Game phases: 'login' or 'game'
  const [phase, setPhase] = useState('login');
  // Login form
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // The main text log from server + user commands
  const [messages, setMessages] = useState([]);
  // The user’s typed text (shown after the `* ` prompt)
  const [command, setCommand] = useState('');

  // Socket.IO reference
  const socketRef = useRef(null);

  // Scroll-to-bottom reference for the text area
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Establish Socket.IO connection on mount
  useEffect(() => {
    socketRef.current = io('http://localhost:8888');

    socketRef.current.on('connect', () => {
      console.log('Connected to backend.');
    });

    // Listen for login results
    socketRef.current.on('loginSuccess', () => {
      setPhase('game');
    });
    socketRef.current.on('loginFailure', (error) => {
      alert(`Login failed: ${error}`);
    });

    // Listen for general messages
    socketRef.current.on('message', (msg) => {
      setMessages((prev) => [...prev, msg]);
    });

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  // Handle login form submit
  const handleLogin = (e) => {
    e.preventDefault();
    socketRef.current.emit('login', { username, password });
  };

  // Handle command submission
  const handleCommandSubmit = (e) => {
    e.preventDefault();
    if (!command.trim()) return;

    // 1) Show the typed command (with "* " prefix) in the message log
    setMessages((prev) => [...prev, `* ${command}`]);

    // 2) Send the command to the server
    socketRef.current.emit('command', command);

    // 3) Clear the command input
    setCommand('');
  };

  // ---------------------------------------------
  //  LOGIN SCREEN
  // ---------------------------------------------
  if (phase === 'login') {
    return (
      <div style={{ fontFamily: 'monospace', height: '100vh', display: 'flex', flexDirection: 'column' }}>
        {/* Purple stats bar (empty for now) */}
        <div style={{ backgroundColor: '#fe01ff', color: '#000', padding: '0.5rem' }}>
          <strong>AI MUD - Login</strong>
        </div>

        {/* Login form area */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ backgroundColor: '#f9f9f9', padding: '2rem', borderRadius: '4px' }}>
            <h2>Login</h2>
            <form onSubmit={handleLogin}>
              <div>
                <label>Username: </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  style={{ marginBottom: '1rem' }}
                />
              </div>
              <div>
                <label>Password: </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  style={{ marginBottom: '1rem' }}
                />
              </div>
              <button type="submit" style={{ padding: '0.5rem' }}>Login</button>
            </form>
          </div>
        </div>

        {/* Yellow input bar is hidden during login phase */}
      </div>
    );
  }

  // ---------------------------------------------
  //  GAME SCREEN
  // ---------------------------------------------
  return (
    <div style={{ fontFamily: 'monospace', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      
      {/* Purple stats bar at the top */}
      <div style={{ backgroundColor: '#fe01ff', color: '#000', padding: '0.5rem' }}>
        <strong>HP: 43/43 | ST: 48 | DEX: 59</strong>  {/* example stats */}
      </div>

      {/* Main text area (retro black/green) */}
      <div style={{
        flex: 1,
        backgroundColor: '#02ffff',
        color: '#000000',
        padding: '0.5rem',
        overflowY: 'auto',
        whiteSpace: 'pre-wrap'  // Ensures line breaks are respected
      }}>
        {messages.map((msg, index) => (
          <pre key={index} style={{ margin: 0 }}>{msg}</pre>
        ))}

        {/* Show the current prompt line at the bottom */}
        <div>
          <span>* </span>
        </div>

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Yellow input bar */}
      <form onSubmit={handleCommandSubmit} style={{ backgroundColor: '#ffff00', padding: '0.5rem' }}>
        <input
          type="text"
          placeholder="Type your command..."
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          style={{
            width: '100%',
            border: 'none',
            outline: 'none',
            backgroundColor: '#ffff00',
            fontFamily: 'monospace'
          }}
        />
      </form>
    </div>
  );
}

export default App;
