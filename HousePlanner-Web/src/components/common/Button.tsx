import React, { type ButtonHTMLAttributes } from 'react';
import Spinner from './Spinner';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger';
  isLoading?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  isLoading = false,
  size = 'md',
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
  
  const variants = {
    primary: 'bg-indigo-600 hover:bg-indigo-700 text-white focus:ring-indigo-500 custom-shadow-sm active:scale-[0.98]',
    secondary: 'bg-zinc-100 hover:bg-zinc-200 text-zinc-800 focus:ring-zinc-500 active:scale-[0.98]',
    outline: 'border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 focus:ring-zinc-500 active:scale-[0.98]',
    danger: 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500 custom-shadow-sm active:scale-[0.98]',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && <Spinner size="sm" className="mr-2 border-current!" />}
      {children}
    </button>
  );
};

export default Button;
