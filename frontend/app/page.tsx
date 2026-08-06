"use client";

import { useState } from "react";

import ChatArea from "@/components/ChatArea";
import Header from "@/components/Header";
import InputBox from "@/components/InputBox";
import Sidebar from "@/components/Sidebar";

import { Message } from "@/types/message";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: "assistant",
      content: "Hello Chandana! 🚀",
    },
  ]);

  const handleSend = (userMessage: string) => {
    const user: Message = {
      id: Date.now(),
      role: "user",
      content: userMessage,
    };

    const ai: Message = {
      id: Date.now() + 1,
      role: "assistant",
      content: `You said: ${userMessage}`,
    };

    setMessages((prev) => [...prev, user, ai]);
  };

  return (
    <div className="flex h-screen">
      <Sidebar />

      <div className="flex flex-col flex-1">
        <Header />

        <ChatArea messages={messages} />

        <InputBox onSend={handleSend} />
      </div>
    </div>
  );
}