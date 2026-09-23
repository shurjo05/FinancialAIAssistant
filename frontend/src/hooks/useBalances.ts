import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";

/** Connected-account balances (shared by Overview and the Ask Jo preview). */
export const useBalances = () => useQuery({ queryKey: ["balances"], queryFn: api.balances });
