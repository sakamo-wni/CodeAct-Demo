// src/lib/agent.ts
export type AgentResponse = {
    parsed: {
      tag_id: string;
      start_dt: string;
      end_dt: string;
    };
    files: string[];
  };
  
  export async function runAgent(nlQuery: string): Promise<AgentResponse> {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/agent/invoke`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: { input: nlQuery } }),
        cache: "no-store",
      },
    );
  
    if (!res.ok) {
      throw new Error(await res.text());
    }
    return res.json();
  }
  