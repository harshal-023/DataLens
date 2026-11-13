import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Mail, Check, X, Building, AlertCircle, ArrowRight } from 'lucide-react';
import {
  collaborationService,
  InvitationPublicDetail,
} from '../../services/collaborationService';
import { useAuth } from '../../context/AuthContext';
import { DataLensLogo } from '../../components/common/DataLensLogo';

export const AcceptInvitation: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  const { user } = useAuth();

  const [details, setDetails] = useState<InvitationPublicDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError('No invitation token found in link.');
      setLoading(false);
      return;
    }

    const fetchDetails = async () => {
      try {
        const data = await collaborationService.getInvitationByToken(token);
        setDetails(data);
      } catch (err: any) {
        setError(err.message || 'Invitation is invalid or has expired.');
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [token]);

  const handleAccept = async () => {
    if (!token) return;
    setProcessing(true);
    try {
      const res = await collaborationService.acceptInvitation(token);
      setSuccessMsg(`Welcome! You have successfully joined ${res.workspace_name}.`);
      setTimeout(() => {
        navigate('/dashboards');
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to accept invitation.');
    } finally {
      setProcessing(false);
    }
  };

  const handleDecline = async () => {
    if (!token) return;
    if (!confirm('Are you sure you want to decline this workspace invitation?')) return;
    setProcessing(true);
    try {
      await collaborationService.declineInvitation(token);
      setSuccessMsg('You have declined the invitation.');
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to decline invitation.');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F0F4F8] flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-elevated border border-[#DCE5EB] p-8 text-center space-y-6 animate-in fade-in duration-200">
        {/* Logo */}
        <div className="flex justify-center">
          <DataLensLogo className="h-8" />
        </div>

        {loading ? (
          <div className="py-8 text-sm text-[#52616C]">Validating invitation link...</div>
        ) : error ? (
          <div className="space-y-4 py-4">
            <div className="w-12 h-12 bg-red-100 text-[#A63838] rounded-full flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-[#102C46]">Invitation Problem</h2>
            <p className="text-xs text-[#52616C]">{error}</p>
            <button
              onClick={() => navigate('/login')}
              className="mt-4 px-4 py-2 bg-[#102C46] text-white text-xs font-bold rounded-xl hover:bg-[#1E3A5F]"
            >
              Back to Login
            </button>
          </div>
        ) : successMsg ? (
          <div className="space-y-4 py-4">
            <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto">
              <Check className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-[#102C46]">Success!</h2>
            <p className="text-xs text-[#52616C]">{successMsg}</p>
          </div>
        ) : details ? (
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="w-12 h-12 bg-[#EDF7FA] text-[#009F98] rounded-full flex items-center justify-center mx-auto">
                <Building className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-[#102C46]">Workspace Invitation</h2>
              <p className="text-xs text-[#52616C]">
                <strong className="text-[#102C46]">{details.inviter_name}</strong> invited you to
                join <strong className="text-[#102C46]">{details.workspace_name}</strong> as an{' '}
                <span className="font-semibold text-[#009F98] uppercase">{details.role}</span>.
              </p>
            </div>

            {user ? (
              <div className="space-y-3 pt-2">
                <p className="text-[11px] text-[#52616C]">
                  Signed in as <strong className="text-[#102C46]">{user.email}</strong>
                </p>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleDecline}
                    disabled={processing}
                    className="flex-1 py-2.5 border border-[#DCE5EB] text-xs font-semibold text-[#52616C] hover:bg-gray-50 rounded-xl"
                  >
                    Decline
                  </button>
                  <button
                    onClick={handleAccept}
                    disabled={processing}
                    className="flex-1 py-2.5 bg-[#009F98] text-white text-xs font-bold rounded-xl hover:bg-[#008781] transition-all shadow-sm"
                  >
                    {processing ? 'Joining...' : 'Accept & Join'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3 pt-2">
                <p className="text-xs text-[#52616C]">
                  Please sign in or create an account to accept this invitation.
                </p>
                <button
                  onClick={() =>
                    navigate(
                      `/login?redirect=${encodeURIComponent(
                        window.location.pathname + window.location.search
                      )}`
                    )
                  }
                  className="w-full py-2.5 bg-[#009F98] text-white text-xs font-bold rounded-xl hover:bg-[#008781] transition-all flex items-center justify-center gap-2"
                >
                  Sign In to Accept <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
};

