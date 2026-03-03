"use client";

import { useState } from "react";

export default function DashboardPage() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <h1>Dashboard</h1>
      <button onClick={() => setCount(count + 1)}>
        {count}
      </button>
    </div>
  );
}