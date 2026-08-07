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

  const [loading, setLoading] = useState(false);

  const handleSend = async (userMessage: string) => {
    const user: Message = {
      id: Date.now(),
      role: "user",
      content: userMessage,
    };

    setMessages((prev) => [...prev, user]);
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
        }),
      });

      const data = await response.json();

      const ai: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: data.reply,
      };

      setMessages((prev) => [...prev, ai]);
    } catch (error) {
      const ai: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: "Backend connection failed",
      };

      setMessages((prev) => [...prev, ai]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar />

      <div className="flex flex-col flex-1">
        <Header />

        <ChatArea
          messages={messages}
          loading={loading}
        />

        <InputBox onSend={handleSend} />
      </div>
    </div>
  );
}