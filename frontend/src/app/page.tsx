"use client";
import { useState } from "react";
import { runAgent } from "@/lib/agent";

export default function Home() {
  const [query, setQuery] = useState("");
  const [resp, setResp] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    setLoading(true);
    try {
      const data = await runAgent(query);
      setResp(JSON.stringify(data, null, 2));
    } catch (err: any) {
      setResp(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="p-6 space-y-4 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold">AI 気象データエージェント</h1>

      <textarea
        className="w-full border rounded p-2"
        rows={3}
        placeholder="441000205 の 2025-04-20 12時〜13時の ru"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      <button
        onClick={handleSend}
        className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        disabled={loading}
      >
        {loading ? "実行中…" : "送信"}
      </button>

      {resp && (
        <pre className="bg-gray-100 p-4 rounded text-xs whitespace-pre-wrap text-gray-800 dark:bg-gray-800 dark:text-gray-200">
          {resp}
        </pre>
      )}
    </main>
  );
}
