"use client";

import { useState } from "react";

export default function InputBox() {
  const [message, setMessage] = useState("");

  return (
    <div className="border-t p-4">
      <input
        type="text"
        placeholder="Ask AI Engineer..."
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        className="w-full border rounded-lg px-4 py-2"
      />

      <p className="mt-2">You typed: {message}</p>
    </div>
  );
}