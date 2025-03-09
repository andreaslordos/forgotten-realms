// App.js
import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';

function App() {
  // Track whether we are in 'login' or 'game' phase
  const [phase, setPhase] = useState("login");

  // Terminal text log
  const [messages, setMessages] = useState(["* "]);

  // Current command input
  const [command, setCommand] = useState("");

  // Whether to show password or text
  const [inputType, setInputType] = useState("text");

  // HUD data
  const [playerName, setPlayerName] = useState("");
  const [playerScore, setPlayerScore] = useState(0);
  const [playerStamina, setPlayerStamina] = useState(0);
  const [maxStamina, setMaxStamina] = useState(0);

  // Whether the input is disabled (e.g., after connection closed)
  const [inputDisabled, setInputDisabled] = useState(false);

  // Socket and ref for scrolling
  const socketRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Establish Socket.IO connection on mount
  useEffect(() => {
    const SOCKET_URL = process.env.NODE_ENV === 'production' 
      ? 'https://api.realms.lordos.tech:8080'  // Use static IP for production
      : 'http://localhost:8080';

    socketRef.current = io(SOCKET_URL, {
      transports: ['websocket'],
      reconnection: false,   // Disable auto-reconnection
      pingInterval: 60000,   // 60 seconds (in ms)
      pingTimeout: 180000,    // 180 seconds (in ms)
    });

    // On successful connect
    socketRef.current.on('connect', () => {
      console.log('Connected to backend.');
    });

    // If the server forcibly disconnects or the connection is lost
    socketRef.current.on('disconnect', () => {
      setMessages((prev) => [...prev, "Connection lost."]);
      setInputDisabled(true);
    });

    // Listen for general messages from the server
    socketRef.current.on('message', (msg) => {
      setMessages((prev) => {
        let newMessages = [...prev];
        if (newMessages.length > 0 && newMessages[newMessages.length - 1] === "* ") {
          newMessages.pop();
        }
        return [...newMessages, msg, "* "];
      });
    });

    // Listen for input type changes (e.g., switching to password mode)
    socketRef.current.on('setInputType', (type) => {
      setInputType(type);
    });

    // Listen for stats updates (HUD)
    socketRef.current.on('statsUpdate', (data) => {
      setPlayerName(data.name);
      setPlayerScore(data.score);
      setPlayerStamina(data.stamina);
      setMaxStamina(data.max_stamina);
      setPhase("game");
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  // Handle command submission
  const handleCommandSubmit = (e) => {
    e.preventDefault();
    if (inputDisabled) {
      return;
    }
  
    // In game phase, if blank input is entered, just add a new prompt line and do nothing else.
    if (command.trim() === "" && phase === "game") {
      setMessages((prev) => [...prev, "* "]);
      setCommand("");
      return;
    }
  
    // For login phase, blank input is allowed and sent to the server.
    let outputCommand = command;
    if (inputType === "password") {
      outputCommand = "*".repeat(command.length);
    }
    setMessages((prev) => {
      let newMessages = [...prev];
      if (newMessages.length > 0 && newMessages[newMessages.length - 1] === "* ") {
        newMessages.pop();
      }
      newMessages.push(`* ${outputCommand}`);
      newMessages.push("* ");
      return newMessages;
    });
    socketRef.current.emit('command', command);
    setCommand("");
  };

  return (
    <>
      {/* CSS to limit output text width and enforce wrapping */}
      <style>{`
        .output-container {
          width: 50vw;
        }
        @media (max-width: 768px) {
          .output-container {
            width: 100%;
          }
        }
        /* Ensure pre elements wrap text properly */
        .output-container pre {
          margin: 0;
          white-space: pre-wrap;
          word-wrap: break-word;
          /* Alternatively, for modern browsers: overflow-wrap: break-word; */
        }
      `}</style>
      <div style={{ fontFamily: "monospace", height: "100vh", display: "flex", flexDirection: "column" }}>
        {/* Top bar / HUD */}
        <div style={{ backgroundColor: "#fe01ff", color: "#000", padding: "0.5rem" }}>
          {playerName
            ? <strong>{playerName} | Score: {playerScore}, Stamina: {playerStamina}/{maxStamina}</strong>
            : <strong>The Forgotten Realms</strong>
          }
        </div>

        {/* Main text area (blue screen) */}
        <div
          style={{
            flex: 1,
            backgroundColor: "#02ffff",
            color: "#000000",
            padding: "0.5rem",
            overflowY: "auto"
          }}
        >
          {/* Wrap text output in a container limited to 50% width */}
          <div className="output-container">
            {messages.map((msg, index) => (
              <pre key={index}>{msg}</pre>
            ))}
          </div>
          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <form onSubmit={handleCommandSubmit} style={{ backgroundColor: "#ffff00", padding: "0.5rem" }}>
          <input
            type={inputType}
            placeholder={inputDisabled ? "Connection Closed" : "Type your command...."}
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            disabled={inputDisabled}
            style={{
              width: "100%",
              border: "none",
              outline: "none",
              backgroundColor: "#ffff00",
              fontFamily: "monospace"
            }}
          />
        </form>
      </div>
    </>
  );
}

export default App;
