import { Link } from "react-router-dom";
import AuthForm from "../components/AuthForm";
import { useAuth } from "../hooks/useAuth";

export default function Register() {
  const { register } = useAuth();
  return (
    <AuthForm
      title="Create account"
      submitLabel="Register"
      onSubmit={register}
      footer={<>Already have an account? <Link to="/login" className="font-medium text-brand-600">Sign in</Link></>}
    />
  );
}
