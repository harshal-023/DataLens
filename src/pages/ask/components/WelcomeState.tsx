import React from 'react';
import {
  Sparkles,
  BarChart3,
  TrendingUp,
  Layers,
  Lightbulb,
} from 'lucide-react';
import { Dataset, User } from '../../../types';

interface WelcomeStateProps {
  user: User;
  selectedDataset?: Dataset;
  suggestedQuestions: string[];
  onSelectQuestion: (question: string) => void;
}

export const WelcomeState: React.FC<WelcomeStateProps> = ({
  user,
  selectedDataset,
  suggestedQuestions,
  onSelectQuestion,
}) => {
  const firstName = user.name ? user.name.split(' ')[0] : 'there';

  const quickActions = [
    {
      title: 'Analyze Performance',
      desc: 'Explore your important business metrics.',
      icon: BarChart3,
      prompt: 'Give me an overview of performance and key metrics',
    },
    {
      title: 'Find Trends',
      desc: 'Discover patterns and changes over time.',
      icon: TrendingUp,
      prompt: 'Show revenue and sales trends over time',
    },
    {
      title: 'Compare Categories',
      desc: 'Compare products, regions, or segments.',
      icon: Layers,
      prompt: 'Compare regional and product performance breakdown',
    },
    {
      title: 'Get Key Insights',
      desc: 'Find important observations in your dataset.',
      icon: Lightbulb,
      prompt: `Give me the key insights and takeaways from ${selectedDataset ? selectedDataset.name : 'this dataset'}`,
    },
  ];

  return (
    <div className="flex-1 flex flex-col justify-center items-center py-6 px-4 max-w-2xl mx-auto w-full select-none text-center">
      {/* Sparkle Icon Circle matching reference */}
      <div className="w-14 h-14 rounded-full bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center text-[#009F98] shadow-sm mb-4">
        <Sparkles className="w-7 h-7 text-[#009F98]" />
      </div>

      {/* Greeting Heading */}
      <h2 className="font-serif text-3xl sm:text-4xl text-[#102C46] tracking-tight">
        Welcome, {firstName}! 👋
      </h2>

      {/* Supporting Text */}
      <p className="text-xs sm:text-sm text-[#52616C] mt-2 max-w-lg leading-relaxed">
        Ask questions about your data in plain English and get trusted, data-backed answers with visual insights.
      </p>

      {/* Four Quick Action Cards matching reference image */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full mt-7 text-left">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <div
              key={action.title}
              onClick={() => onSelectQuestion(action.prompt)}
              className="bg-white rounded-2xl border border-[#DCE5EB] p-3.5 hover:border-[#009F98] hover:shadow-subtle transition-all duration-200 cursor-pointer group flex flex-col justify-between"
            >
              <div className="w-8 h-8 rounded-xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center text-[#009F98] mb-2 group-hover:scale-105 transition-transform">
                <Icon className="w-4 h-4 text-[#009F98]" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-[#102C46] group-hover:text-[#009F98] transition-colors leading-tight">
                  {action.title}
                </h4>
                <p className="text-[10px] text-[#52616C] mt-1 leading-snug">
                  {action.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Suggested Questions Section */}
      <div className="w-full mt-7 pt-5 border-t border-[#EEF3F6]">
        <p className="text-xs font-bold text-[#102C46] mb-3">Try asking something like:</p>

        {selectedDataset ? (
          <div className="flex flex-wrap items-center justify-center gap-2">
            {suggestedQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => onSelectQuestion(q)}
                className="px-3.5 py-1.5 rounded-full border border-[#DCE5EB] bg-white hover:border-[#009F98] hover:bg-[#EDF7FA] text-xs text-[#102C46] font-medium transition-all cursor-pointer shadow-2xs"
              >
                {q}
              </button>
            ))}
          </div>
        ) : (
          <p className="text-xs text-[#52616C] italic">
            Select a dataset from the right panel to see relevant analytical questions.
          </p>
        )}
      </div>
    </div>
  );
};

