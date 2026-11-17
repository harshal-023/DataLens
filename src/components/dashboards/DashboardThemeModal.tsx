import React from 'react';
import { Palette, Check, Sparkles, X } from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { DASHBOARD_THEMES, DashboardTheme } from './DashboardThemes';

export interface DashboardThemeModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentThemeId: string;
  onSelectTheme: (themeId: string) => void;
}

export const DashboardThemeModal: React.FC<DashboardThemeModalProps> = ({
  isOpen,
  onClose,
  currentThemeId,
  onSelectTheme,
}) => {
  const themes = Object.values(DASHBOARD_THEMES);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Dashboard Appearance & Theme"
      maxWidth="md"
    >
      <div className="space-y-4 pt-1">
        <p className="text-xs text-[#52616C]">
          Select an aesthetic theme for your dashboard canvas and widget cards. Changes are instantly previewed and saved with your layout.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          {themes.map((theme) => {
            const isSelected = theme.id === currentThemeId;

            return (
              <button
                key={theme.id}
                type="button"
                onClick={() => {
                  onSelectTheme(theme.id);
                  onClose();
                }}
                className={`text-left p-3.5 rounded-xl border-2 transition-all cursor-pointer relative flex flex-col justify-between ${
                  isSelected
                    ? 'border-[#009F98] ring-2 ring-[#009F98]/20 bg-emerald-50/20 shadow-xs'
                    : 'border-[#DCE5EB] hover:border-slate-300 hover:shadow-2xs bg-white'
                }`}
              >
                {/* Theme Color Palette Preview Bar */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-4 h-4 rounded-full border border-black/10 shadow-xs"
                      style={{ backgroundColor: theme.canvasBg }}
                    />
                    <span
                      className="w-4 h-4 rounded-full border border-black/10 shadow-xs"
                      style={{ backgroundColor: theme.cardBg }}
                    />
                    <span
                      className="w-4 h-4 rounded-full shadow-xs"
                      style={{ backgroundColor: theme.accent }}
                    />
                  </div>

                  {isSelected && (
                    <span className="w-5 h-5 rounded-full bg-[#009F98] text-white flex items-center justify-center">
                      <Check className="w-3.5 h-3.5 stroke-[3]" />
                    </span>
                  )}
                </div>

                <div>
                  <h4 className="text-xs font-bold text-[#102C46] flex items-center gap-1.5">
                    {theme.name}
                    {theme.id === 'clean_light' && (
                      <span className="text-[10px] font-normal text-[#009F98] bg-[#EDF7FA] px-1.5 py-0.2 rounded font-mono">
                        Default
                      </span>
                    )}
                  </h4>
                  <p className="text-[11px] text-[#52616C] mt-0.5 leading-snug">
                    {theme.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        <div className="pt-4 border-t border-[#DCE5EB] flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
};
