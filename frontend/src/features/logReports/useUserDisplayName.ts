import { useEffect, useState } from "react";
import axios from "axios";

export function useUserDisplayName(userId?: number | null) {
  const [displayName, setDisplayName] = useState<string>("");

  useEffect(() => {
    if (!userId) {
      setDisplayName("");
      return;
    }
    let cancelled = false;
    axios.get(`/api/v1/users/${userId}`)
      .then(res => {
        if (!cancelled) {
          const user = res.data;
          setDisplayName(user.full_name || user.email || `User #${userId}`);
        }
      })
      .catch(() => {
        if (!cancelled) setDisplayName(`User #${userId}`);
      });
    return () => { cancelled = true; };
  }, [userId]);

  return displayName;
}
