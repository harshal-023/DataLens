import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Eye,
  EyeOff,
  TrendingUp,
  MessageSquare,
  FlaskConical,
  FileText,
  Mail,
  Lock,
  User as UserIcon,
  Sparkles,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';
import { DataLensLogo } from '../../components/common/DataLensLogo';
import { useAuth } from '../../context/AuthContext';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, register, forgotPassword } = useAuth();

  const [activeTab, setActiveTab] = useState<'login' | 'signup' | 'forgot'>('login');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('harshal@datalens.ai');
  const [password, setPassword] = useState('SecurePass123!');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const from = (location.state as any)?.from?.pathname || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');

    if (activeTab === 'forgot') {
      if (!email) {
        setError('Please enter your email address.');
        return;
      }
      setIsLoading(true);
      try {
        const msg = await forgotPassword(email);
        setSuccessMessage(msg || 'Password reset link sent to your email.');
      } catch (err: any) {
        setError(err.message || 'Failed to dispatch password reset link.');
      } finally {
        setIsLoading(false);
      }
      return;
    }

    if (!email || !password) {
      setError('Please provide both email and password.');
      return;
    }

    if (activeTab === 'signup' && !fullName.trim()) {
      setError('Please enter your full name.');
      return;
    }

    setIsLoading(true);
    try {
      if (activeTab === 'login') {
        await login(email, password);
      } else {
        await register(fullName, email, password);
      }
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F8FA] flex items-center justify-center p-4 sm:p-6 lg:p-12 relative overflow-hidden font-sans">
      {/* Background ambient lighting/glow */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-[#DDF0F5]/50 rounded-full blur-3xl pointer-events-none -z-0" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-[#009F98]/10 rounded-full blur-3xl pointer-events-none -z-0" />

      <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center relative z-10">
        {/* Left Side: Brand Story & Features */}
        <div className="lg:col-span-7 flex flex-col justify-between space-y-8 py-2">
          {/* Logo at top */}
          <div>
            <DataLensLogo size="lg" theme="light" />
          </div>

          <div className="space-y-6">
            {/* Teal-outlined pill badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-[#BBDCE8] bg-[#EDF7FA] text-[#007D78] text-xs font-semibold shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-[#009F98]" />
              <span>AI-Powered Business Intelligence</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#102C46] leading-[1.12]">
              Your Data <br />
              Tells a <span className="font-serif italic font-normal text-[#009F98]">Bigger</span> <br />
              Story
            </h1>

            {/* 4 Feature Rows */}
            <div className="space-y-3.5 pt-2 max-w-lg">
              <div className="flex items-center gap-3.5">
                <div className="w-8 h-8 rounded-lg bg-[#EDF7FA] flex items-center justify-center text-[#007D78] shrink-0 shadow-2xs border border-[#BBDCE8]">
                  <TrendingUp className="w-4 h-4 text-[#009F98]" />
                </div>
                <span className="text-sm font-semibold text-[#102C46]">
                  Turn raw data into clear insights
                </span>
              </div>

              <div className="flex items-center gap-3.5">
                <div className="w-8 h-8 rounded-lg bg-[#EDF7FA] flex items-center justify-center text-[#007D78] shrink-0 shadow-2xs border border-[#BBDCE8]">
                  <MessageSquare className="w-4 h-4 text-[#009F98]" />
                </div>
                <span className="text-sm font-semibold text-[#102C46]">
                  Ask business questions in natural language
                </span>
              </div>

              <div className="flex items-center gap-3.5">
                <div className="w-8 h-8 rounded-lg bg-[#EDF7FA] flex items-center justify-center text-[#007D78] shrink-0 shadow-2xs border border-[#BBDCE8]">
                  <FlaskConical className="w-4 h-4 text-[#009F98]" />
                </div>
                <span className="text-sm font-semibold text-[#102C46]">
                  Experiment with prompt strategies
                </span>
              </div>

              <div className="flex items-center gap-3.5">
                <div className="w-8 h-8 rounded-lg bg-[#EDF7FA] flex items-center justify-center text-[#007D78] shrink-0 shadow-2xs border border-[#BBDCE8]">
                  <FileText className="w-4 h-4 text-[#009F98]" />
                </div>
                <span className="text-sm font-semibold text-[#102C46]">
                  Generate professional reports
                </span>
              </div>
            </div>
          </div>

          {/* Illustrative preview cards stack */}
          <div className="pt-2 hidden sm:flex items-center gap-4 opacity-90">
            <div className="bg-white border border-[#DCE5EB] rounded-xl px-4 py-2.5 shadow-subtle flex items-center gap-3">
              <span className="text-[11px] text-[#52616C]">Sales Growth</span>
              <span className="text-xs font-bold text-[#216548] bg-[#E4F3EC] px-2 py-0.5 rounded-full">+32% ↑</span>
            </div>
            <div className="bg-white border border-[#DCE5EB] rounded-xl px-4 py-2.5 shadow-subtle flex items-center gap-3">
              <span className="text-[11px] text-[#52616C]">Top Product</span>
              <span className="text-xs font-bold text-[#102C46]">Premium Pro</span>
            </div>
            <div className="bg-white border border-[#DCE5EB] rounded-xl px-4 py-2.5 shadow-subtle flex items-center gap-3">
              <span className="text-[11px] text-[#52616C]">Revenue</span>
              <span className="text-xs font-bold text-[#009F98]">₹ 1.24M</span>
            </div>
          </div>
        </div>

        {/* Right Side: Auth Card */}
        <div className="lg:col-span-5 flex justify-center">
          <div className="w-full max-w-[460px] bg-white rounded-2xl border border-[#DCE5EB] shadow-elevated p-8 sm:p-10 relative">
            {/* Centered Logo Bar */}
            <div className="flex flex-col items-center justify-center mb-4">
              <div className="flex items-end gap-1.5 mb-3">
                <div className="w-2 h-4 bg-[#009F98] rounded-full" />
                <div className="w-2 h-6 bg-[#39C3B8] rounded-full" />
                <div className="w-2 h-8 bg-[#8BE5DE] rounded-full" />
              </div>
              <h2 className="text-2xl font-bold text-[#102C46] tracking-tight">
                {activeTab === 'login' && 'Welcome Back'}
                {activeTab === 'signup' && 'Create Your Account'}
                {activeTab === 'forgot' && 'Reset Password'}
              </h2>
              <p className="text-xs text-[#52616C] mt-1">
                {activeTab === 'login' && 'Sign in to access your business intelligence workspace'}
                {activeTab === 'signup' && 'Get started with verified analytical reports in seconds'}
                {activeTab === 'forgot' && 'Enter your email to receive a secure password reset link'}
              </p>
            </div>

            {/* Login & Sign Up Tabs */}
            {activeTab !== 'forgot' ? (
              <div className="flex border-b border-[#DCE5EB] mb-6 mt-4">
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab('login');
                    setError('');
                    setSuccessMessage('');
                  }}
                  className={`flex-1 pb-2.5 text-center text-xs font-bold transition-colors cursor-pointer relative ${
                    activeTab === 'login' ? 'text-[#009F98]' : 'text-[#52616C] hover:text-[#102C46]'
                  }`}
                >
                  Login
                  {activeTab === 'login' && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#009F98]" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab('signup');
                    setError('');
                    setSuccessMessage('');
                  }}
                  className={`flex-1 pb-2.5 text-center text-xs font-bold transition-colors cursor-pointer relative ${
                    activeTab === 'signup' ? 'text-[#009F98]' : 'text-[#52616C] hover:text-[#102C46]'
                  }`}
                >
                  Sign Up
                  {activeTab === 'signup' && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#009F98]" />
                  )}
                </button>
              </div>
            ) : (
              <div className="mb-6 mt-4 flex items-center justify-between border-b border-[#DCE5EB] pb-2.5">
                <span className="text-xs font-bold text-[#009F98]">Password Recovery</span>
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab('login');
                    setError('');
                    setSuccessMessage('');
                  }}
                  className="text-xs text-[#52616C] hover:text-[#102C46] font-medium"
                >
                  ← Back to Login
                </button>
              </div>
            )}

            {error && (
              <div className="mb-4 p-3 rounded-xl bg-[#FCE9E9] border border-[#F7C9C5] text-xs text-[#A63838] flex items-center gap-2">
                <span>{error}</span>
              </div>
            )}

            {successMessage && (
              <div className="mb-4 p-3 rounded-xl bg-[#E4F3EC] border border-[#BCE4D1] text-xs text-[#216548] flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#216548] shrink-0" />
                <span>{successMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {activeTab === 'signup' && (
                <div>
                  <label className="sr-only">Full Name</label>
                  <div className="relative">
                    <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#52616C]" />
                    <input
                      type="text"
                      required
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Full Name (e.g. Harshal Sharma)"
                      className="w-full pl-10 pr-3.5 py-2.5 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] placeholder:text-[#52616C] focus:outline-none focus:ring-2 focus:ring-[#009F98]"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="sr-only">Email address</label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#52616C]" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Email address"
                    className="w-full pl-10 pr-3.5 py-2.5 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] placeholder:text-[#52616C] focus:outline-none focus:ring-2 focus:ring-[#009F98]"
                  />
                </div>
              </div>

              {activeTab !== 'forgot' && (
                <div>
                  <label className="sr-only">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#52616C]" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={activeTab === 'signup' ? 'Password (min 8 chars, 1 uppercase, 1 digit)' : 'Password'}
                      className="w-full pl-10 pr-10 py-2.5 text-xs rounded-xl border border-[#DCE5EB] bg-white text-[#102C46] placeholder:text-[#52616C] focus:outline-none focus:ring-2 focus:ring-[#009F98]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[#52616C] hover:text-[#102C46] cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              )}

              {activeTab === 'login' && (
                <div className="flex items-center justify-between text-xs pt-1">
                  <label className="flex items-center gap-2 text-[#52616C] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="rounded border-[#DCE5EB] text-[#009F98] focus:ring-[#009F98]"
                    />
                    <span>Remember me</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveTab('forgot');
                      setError('');
                      setSuccessMessage('');
                    }}
                    className="text-xs text-[#009F98] hover:underline font-semibold cursor-pointer"
                  >
                    Forgot password?
                  </button>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 mt-2 rounded-xl bg-[#009F98] hover:bg-[#007D78] active:bg-[#086E73] text-white text-xs font-bold shadow-[0_2px_12px_rgba(0,159,152,0.3)] flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
              >
                <span>
                  {isLoading
                    ? 'Processing...'
                    : activeTab === 'login'
                    ? 'Sign In →'
                    : activeTab === 'signup'
                    ? 'Create Account →'
                    : 'Send Reset Link →'}
                </span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export const SignUpPage: React.FC = () => {
  return <LoginPage />;
};

export const ForgotPasswordPage: React.FC = () => {
  return <LoginPage />;
};

export const ResetPasswordPage: React.FC = () => {
  return <LoginPage />;
};

export const OnboardingPage: React.FC = () => {
  return <LoginPage />;
};
