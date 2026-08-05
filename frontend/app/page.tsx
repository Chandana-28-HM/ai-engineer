import Sidebar from "@/components/Sidebar";
import ChatArea from "@/components/ChatArea";

export default function Home() {
  return (
    <main className="flex h-screen">
      <Sidebar />
      <ChatArea />
    </main>
  );
}