"use client";

import Link from "next/link";

export default function Navbar() {
  return (
    <nav style={{ padding: "10px", background: "#111", color: "white" }}>
      <Link href="/">Home</Link> |{" "}
      <Link href="/dashboard">Dashboard</Link> |{" "}
      <Link href="/upload">Upload</Link>
    </nav>
  );
}


