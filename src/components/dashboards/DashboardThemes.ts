// Dashboard Palettes and Themes System

export interface ColorPalette {
  id: string;
  name: string;
  description: string;
  colors: string[];
  primary: string;
  wash: string; // Pastel wash for KPI cards
}

export const COLOR_PALETTES: Record<string, ColorPalette> = {
  ocean: {
    id: 'ocean',
    name: 'Ocean (Default)',
    description: 'DataLens signature peacock teal, light teal, and navy tones',
    primary: '#009F98',
    wash: '#EDF8F7',
    colors: ['#009F98', '#39C3B8', '#102C46', '#8BE5DE', '#1D4664', '#007D78'],
  },
  sunset: {
    id: 'sunset',
    name: 'Sunset',
    description: 'Warm coral, amber, and golden rose gradients',
    primary: '#F97316',
    wash: '#FEF7EC',
    colors: ['#F97316', '#F59E0B', '#F43F5E', '#FDBA74', '#FACC15', '#EA580C'],
  },
  forest: {
    id: 'forest',
    name: 'Forest',
    description: 'Fresh emerald, sage, and mint greens',
    primary: '#10B981',
    wash: '#ECFDF5',
    colors: ['#10B981', '#34D399', '#059669', '#047857', '#84CC16', '#065F46'],
  },
  royal: {
    id: 'royal',
    name: 'Royal',
    description: 'Deep violet, purple, and soft lavender',
    primary: '#8B5CF6',
    wash: '#F6F0FA',
    colors: ['#8B5CF6', '#6366F1', '#A855F7', '#C084FC', '#4C1D95', '#7C3AED'],
  },
  business: {
    id: 'business',
    name: 'Business',
    description: 'Classic corporate blue, navy, and slate',
    primary: '#2563EB',
    wash: '#EDF5FB',
    colors: ['#2563EB', '#1E40AF', '#3B82F6', '#60A5FA', '#1E293B', '#475569'],
  },
  vibrant: {
    id: 'vibrant',
    name: 'Vibrant',
    description: 'Dynamic multi-color rainbow for rich categorization',
    primary: '#009F98',
    wash: '#EDF8F7',
    colors: ['#009F98', '#8B5CF6', '#F59E0B', '#EC4899', '#10B981', '#3B82F6'],
  },
  monochrome: {
    id: 'monochrome',
    name: 'Monochrome',
    description: 'Sleek greyscale and charcoal for minimalist reporting',
    primary: '#334155',
    wash: '#F8FAFC',
    colors: ['#0F172A', '#334155', '#475569', '#64748B', '#94A3B8', '#CBD5E1'],
  },
};

export const getPaletteColors = (paletteId?: string, customColor?: string): string[] => {
  if (customColor && customColor.startsWith('#')) {
    const basePalette = COLOR_PALETTES[paletteId || 'ocean'] || COLOR_PALETTES.ocean;
    return [customColor, ...basePalette.colors.filter((c) => c.toLowerCase() !== customColor.toLowerCase())];
  }
  const palette = COLOR_PALETTES[paletteId || 'ocean'] || COLOR_PALETTES.ocean;
  return palette.colors;
};

export const getPalettePrimary = (paletteId?: string, customColor?: string): string => {
  if (customColor && customColor.startsWith('#')) return customColor;
  const palette = COLOR_PALETTES[paletteId || 'ocean'] || COLOR_PALETTES.ocean;
  return palette.primary;
};

// ---------------------------------------------------------------------------
// Dashboard Theme Presets
// ---------------------------------------------------------------------------

export interface DashboardTheme {
  id: string;
  name: string;
  description: string;
  canvasBg: string;
  cardBg: string;
  borderColor: string;
  textPrimary: string;
  textMuted: string;
  headerBg: string;
  accent: string;
  previewClass: string;
}

export const DASHBOARD_THEMES: Record<string, DashboardTheme> = {
  clean_light: {
    id: 'clean_light',
    name: 'Clean Light',
    description: 'Modern crisp white cards with soft slate borders (Default)',
    canvasBg: '#F5F8FA',
    cardBg: '#FFFFFF',
    borderColor: '#DCE5EB',
    textPrimary: '#102C46',
    textMuted: '#52616C',
    headerBg: '#FFFFFF',
    accent: '#009F98',
    previewClass: 'bg-[#F5F8FA] border-[#DCE5EB]',
  },
  soft_grey: {
    id: 'soft_grey',
    name: 'Soft Grey',
    description: 'Gentle neutral grey tones with muted borders',
    canvasBg: '#ECEFF2',
    cardBg: '#F8FAFC',
    borderColor: '#CBD5E1',
    textPrimary: '#0F172A',
    textMuted: '#475569',
    headerBg: '#FFFFFF',
    accent: '#0284C7',
    previewClass: 'bg-[#ECEFF2] border-[#CBD5E1]',
  },
  midnight: {
    id: 'midnight',
    name: 'Midnight',
    description: 'Executive dark theme with high-contrast glowing charts',
    canvasBg: '#0B1926',
    cardBg: '#132537',
    borderColor: '#1F3851',
    textPrimary: '#F1F5F9',
    textMuted: '#94A3B8',
    headerBg: '#132537',
    accent: '#38BDF8',
    previewClass: 'bg-[#0B1926] border-[#1F3851] text-white',
  },
  ocean: {
    id: 'ocean',
    name: 'Ocean',
    description: 'Refreshing aquatic tint with vibrant teal borders',
    canvasBg: '#EBF5F6',
    cardBg: '#FFFFFF',
    borderColor: '#BBDCE8',
    textPrimary: '#0E3B43',
    textMuted: '#3C6D77',
    headerBg: '#FFFFFF',
    accent: '#009F98',
    previewClass: 'bg-[#EBF5F6] border-[#BBDCE8]',
  },
  minimal_white: {
    id: 'minimal_white',
    name: 'Minimal White',
    description: 'Borderless paper aesthetic with ultra-clean presentation',
    canvasBg: '#FFFFFF',
    cardBg: '#FFFFFF',
    borderColor: '#F1F5F9',
    textPrimary: '#111827',
    textMuted: '#6B7280',
    headerBg: '#FFFFFF',
    accent: '#102C46',
    previewClass: 'bg-white border-slate-100',
  },
};

export const getDashboardTheme = (themeId?: string): DashboardTheme => {
  return DASHBOARD_THEMES[themeId || 'clean_light'] || DASHBOARD_THEMES.clean_light;
};

