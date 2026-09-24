import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useAuth } from "./useAuth";

/** Sign-out actions shared by the desktop sidebar and the phone "More" sheet. */
export function useSignOut() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const signOut = () => {
    logout();
    navigate("/login");
  };

  const signOutEverywhere = async () => {
    try { await api.logoutAll(); } catch { /* best-effort; sign out anyway */ }
    signOut();
  };

  return { signOut, signOutEverywhere };
}
