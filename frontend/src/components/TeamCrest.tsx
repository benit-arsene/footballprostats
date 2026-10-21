"use client";

import { useState } from "react";

type Props = {
  url?: string | null;
  alt?: string;
  className?: string;
  fallback?: React.ReactNode;
};

export default function TeamCrest({ url, alt = "", className = "h-5 w-5 object-contain", fallback }: Props) {
  const [failed, setFailed] = useState(false);

  if (!url || failed) {
    return fallback ? <>{fallback}</> : null;
  }

  /* eslint-disable-next-line @next/next/no-img-element */
  return <img src={url} alt={alt} className={className} onError={() => setFailed(true)} />;
}