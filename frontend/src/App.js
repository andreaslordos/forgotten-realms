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
    socketRef.current = io('https://my-mud-service-225193993451.us-central1.run.app', {
      transports: ['websocket'] // optional
    });

    // useEffect(() => {
    //   socketRef.current = io('https://my-mud-service-225193993451.us-central1.run.app', {
    //     transports: ['websocket'] // optional
    //   });

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

    // Listen for loginSuccess event to switch to game phase
    socketRef.current.on('loginSuccess', () => {
      setPhase("game");
    });

    // Listen for stats updates (HUD)
    socketRef.current.on('statsUpdate', (data) => {
      setPlayerName(data.name);
      setPlayerScore(data.score);
      setPlayerStamina(data.stamina);
      setMaxStamina(data.max_stamina);
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
    // If input is disabled, ignore
    if (inputDisabled) {
      return;
    }

    // In game phase, if blank input is entered, just add a new prompt
    if (command === "" && phase === "game") {
      setMessages((prev) => {
        let newMessages = [...prev];
        if (newMessages.length > 0 && newMessages[newMessages.length - 1] === "* ") {
          newMessages.pop();
        }
        return [...newMessages, "* "];
      });
      return;
    }

    // For login phase, blank input is allowed and sent to the server
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
    <div style={{ fontFamily: "monospace", height: "100vh", display: "flex", flexDirection: "column" }}>

      {/* Top bar / HUD */}
      <div style={{ backgroundColor: "#fe01ff", color: "#000", padding: "0.5rem" }}>
        {playerName
          ? <strong>{playerName} | Score: {playerScore}, Stamina: {playerStamina}/{maxStamina}</strong>
          : <strong>The Forgotten Realms</strong>
        }
      </div>

      {/* Main text area */}
      <div
        style={{
          flex: 1,
          backgroundColor: "#02ffff",
          color: "#000000",
          padding: "0.5rem",
          overflowY: "auto",
          whiteSpace: "pre-wrap"
        }}
      >
        {messages.map((msg, index) => (
          <pre key={index} style={{ margin: 0 }}>{msg}</pre>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <form onSubmit={handleCommandSubmit} style={{ backgroundColor: "#ffff00", padding: "0.5rem" }}>
        <input
          type={inputType}
          placeholder={inputDisabled ? "Connection Closed" : "Type your command....."}
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
  );
}

export default App;
