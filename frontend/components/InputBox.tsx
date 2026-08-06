"use client";

import { useState } from "react";

interface InputBoxProps {
  onSend: (message: string) => void;
}

export default function InputBox({ onSend }: InputBoxProps) {
  const [message, setMessage] = useState("");

  const handleSend = () => {
    if (!message.trim()) return;

    onSend(message);
    setMessage("");
  };

  return (
    <div className="border-t p-4 flex gap-2">
      <input
        type="text"
        value={message}
        placeholder="Ask AI Engineer..."
        onChange={(e) => setMessage(e.target.value)}
        className="flex-1 border rounded-lg px-4 py-2"
      />

      <button
        onClick={handleSend}
        className="bg-blue-500 text-white px-4 py-2 rounded-lg"
      >
        Send
      </button>
    </div>
  );
}