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

  // Command history
  const [commandHistory, setCommandHistory] = useState([]);
  const [historyPosition, setHistoryPosition] = useState(0);

  // Whether to show password or text
  const [inputType, setInputType] = useState("text");

  // HUD data
  const [playerName, setPlayerName] = useState("");
  const [playerScore, setPlayerScore] = useState(0);
  const [playerStamina, setPlayerStamina] = useState(0);
  const [maxStamina, setMaxStamina] = useState(0);

  // Whether the input is disabled (e.g., after connection closed)
  const [inputDisabled, setInputDisabled] = useState(false);

  // Socket and refs for scrolling and input selection
  const socketRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

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
      return;
    }

    // For password input, never allow blank submissions
    if (command.trim() === "" && inputType === "password") {
      return; // Simply do nothing - don't send blank passwords
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

    // Only clear input during auth phase, keep it in game phase
    if (phase !== "game") {
      setCommand("");
    } else {
      // Add command to history if it has content and isn't a duplicate of the last command
      if (command.trim() !== "") {
        setCommandHistory(prevHistory => {
          if (prevHistory.length === 0 || prevHistory[0] !== command) {
            return [command, ...prevHistory]; // Add to front of array
          }
          return prevHistory;
        });
      }

      // Reset history position
      setHistoryPosition(0);

      // Select all text for easy overtyping
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.select();
        }
      }, 10);
    }
  };

  // Handle up/down arrow keys for command history
  const handleKeyDown = (e) => {
    // Only process in game phase
    if (phase !== "game") {
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();

      // If we're already at the end of history, don't go further
      if (historyPosition >= commandHistory.length) {
        return;
      }

      // If we're at position 0 (current command) and it's not in history yet,
      // and it has content, add it to history
      if (historyPosition === 0 && command.trim() !== "" &&
          (commandHistory.length === 0 || commandHistory[0] !== command)) {
        setCommandHistory(prev => [command, ...prev]);
      }

      // Move to the next position in history
      const newPosition = historyPosition + 1;
      setHistoryPosition(newPosition);

      // Set command to the history item (if available)
      if (newPosition <= commandHistory.length) {
        setCommand(commandHistory[newPosition - 1]);
      }
    }
    else if (e.key === "ArrowDown") {
      e.preventDefault();

      // If we're at position 0, can't go further down
      if (historyPosition <= 0) {
        return;
      }

      // Move to previous position in history
      const newPosition = historyPosition - 1;
      setHistoryPosition(newPosition);

      // If we're back to position 0, clear command
      if (newPosition === 0) {
        setCommand("");
      } else {
        // Set command to the history item
        setCommand(commandHistory[newPosition - 1]);
      }
    }
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
            ref={inputRef}
            type={inputType}
            placeholder={inputDisabled ? "Connection Closed" : "Type your command...."}
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={handleKeyDown}
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
