// App.js
import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';

function App() {
  const [phase, setPhase] = useState("login"); // "login" initially, then "game" after loginSuccess
  const [messages, setMessages] = useState(["* "]); // start with an empty prompt line
  const [command, setCommand] = useState("");
  const [inputType, setInputType] = useState("text"); // "text" or "password"
  const socketRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when messages change.
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Establish Socket.IO connection.
  useEffect(() => {
    socketRef.current = io('http://localhost:8888');

    socketRef.current.on('connect', () => {
      console.log('Connected to backend.');
    });

    // Listen for general messages from the server.
    socketRef.current.on('message', (msg) => {
      setMessages((prev) => {
        let newMessages = [...prev];
        if (newMessages.length > 0 && newMessages[newMessages.length - 1] === "* ") {
          newMessages.pop();
        }
        return [...newMessages, msg, "* "];
      });
    });

    // Listen for input type changes (e.g., switching to password mode).
    socketRef.current.on('setInputType', (type) => {
      setInputType(type);
    });

    // Listen for loginSuccess event to switch to game phase.
    socketRef.current.on('loginSuccess', () => {
      setPhase("game");
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  // Handle command submission.
  const handleCommandSubmit = (e) => {
    e.preventDefault();
    // In game phase, if blank input is entered, just add a new prompt.
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
    <div style={{ fontFamily: "monospace", height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Stats bar (if any) */}
      <div style={{ backgroundColor: "#fe01ff", color: "#000", padding: "0.5rem" }}>
        <strong>Forgotten Realms</strong>
      </div>
      {/* Main text log area */}
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
          placeholder="Type your command..."
          value={command}
          onChange={(e) => setCommand(e.target.value)}
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
