import { Link } from "react-router-dom";
import AuthForm from "../components/AuthForm";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const { login } = useAuth();
  return (
    <AuthForm
      title="Sign in"
      submitLabel="Sign in"
      onSubmit={login}
      footer={<>No account? <Link to="/register" className="font-medium text-accent-ink hover:underline">Register</Link></>}
    />
  );
}
