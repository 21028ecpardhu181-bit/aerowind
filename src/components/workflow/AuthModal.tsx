import React, { useState } from 'react';
import { X, Eye, EyeOff, CheckCircle2, User, Mail, Lock } from 'lucide-react';
import { authLogin, authRegister } from '../../services/api';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthSuccess: (user: { username: string; email: string; token: string }) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onAuthSuccess,
}) => {
  const [isLoginMode, setIsLoginMode] = useState<boolean>(true);
  const [email, setEmail] = useState<string>('engineer1@aeroquantum.com');
  const [username, setUsername] = useState<string>('engineer1');
  const [password, setPassword] = useState<string>('securepassword123');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setIsLoading(true);

    try {
      if (isLoginMode) {
        const res = await authLogin({ username, password });
        localStorage.setItem('aqw_token', res.access_token);
        localStorage.setItem('aqw_user', JSON.stringify({ username: res.username, email: res.email }));
        onAuthSuccess({ username: res.username, email: res.email, token: res.access_token });
        onClose();
      } else {
        const res = await authRegister({ username, email, password });
        localStorage.setItem('aqw_token', res.access_token);
        localStorage.setItem('aqw_user', JSON.stringify({ username: res.username, email: res.email }));
        onAuthSuccess({ username: res.username, email: res.email, token: res.access_token });
        onClose();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication error. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div id="auth-modal" className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-md">
      <div className="relative w-full max-w-sm bg-white rounded-3xl shadow-2xl overflow-hidden border border-white/80 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Close Button */}
        <button
          id="btn-close-auth"
          onClick={onClose}
          className="absolute top-3 right-3 z-10 p-1.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Hero Robot Illustration */}
        <div className="relative bg-gradient-to-b from-amber-50 to-white pt-6 pb-2 px-6 flex flex-col items-center">
          <div className="bg-white/90 backdrop-blur-md px-3 py-1 rounded-full shadow-xs border border-amber-200 text-[11px] font-bold text-amber-900 mb-2">
            Hi! Welcome to AeroQuantum AI Bot
          </div>
          <img
            src="/assets/auth/robot-login-hero.webp"
            alt="AeroQuantum AI Assistant"
            onError={(e) => { (e.currentTarget as any).src = '/assets/real-turbines-photo.jpg'; }}
            className="w-24 h-24 object-contain drop-shadow-md"
          />
        </div>

        {/* Form Body */}
        <div className="p-6 pt-2">
          <h2 id="auth-form-title" className="text-lg font-black text-slate-900 tracking-tight text-center mb-1">
            {isLoginMode ? 'Sign In to AeroQuantum' : 'Create Engineer Account'}
          </h2>
          <p className="text-xs text-slate-500 text-center mb-4">
            {isLoginMode ? 'Enter credentials to access certified simulations' : 'Join AeroQuantum-Wind optimization workspace'}
          </p>

          <form id="auth-form" onSubmit={handleSubmit} className="flex flex-col gap-3">
            {!isLoginMode && (
              <div>
                <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  Work E-mail
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
                  <input
                    id="auth-email-input"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="engineer@aeroquantum.com"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-slate-50 border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#FFD21F]"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Username / Organization
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
                <input
                  id="auth-username-input"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="engineer1"
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-slate-50 border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#FFD21F]"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
                <input
                  id="auth-password-input"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-10 py-2 text-xs rounded-xl bg-slate-50 border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#FFD21F]"
                />
                <button
                  type="button"
                  id="btn-toggle-password"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-700"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {errorMsg && (
              <div id="auth-error-msg" className="p-2 rounded-xl bg-red-50 text-red-700 text-xs font-medium border border-red-200">
                {errorMsg}
              </div>
            )}

            <button
              type="submit"
              id="btn-auth-submit"
              disabled={isLoading}
              className="w-full py-2.5 mt-1 rounded-xl bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 font-black text-xs shadow-md transition-all active:scale-95 disabled:opacity-50"
            >
              {isLoading ? 'Processing...' : isLoginMode ? 'LOG IN' : 'CREATE ACCOUNT'}
            </button>
          </form>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-center gap-1.5 text-xs text-slate-600">
            <span id="auth-toggle-prompt">
              {isLoginMode ? "Don't have an account?" : 'Already have an account?'}
            </span>
            <button
              type="button"
              id="btn-toggle-auth-mode"
              onClick={() => {
                setIsLoginMode(!isLoginMode);
                setErrorMsg('');
              }}
              className="font-bold text-amber-700 hover:text-amber-800 underline"
            >
              {isLoginMode ? 'Sign Up' : 'Log In'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
