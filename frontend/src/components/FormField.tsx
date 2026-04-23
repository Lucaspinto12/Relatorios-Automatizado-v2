import { InputHTMLAttributes, forwardRef } from 'react'

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  hint?: string
  error?: string
}

export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  ({ label, hint, error, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-300">
          {label}
          {props.required && <span className="text-red-400 ml-1">*</span>}
        </label>
        <input
          ref={ref}
          {...props}
          className={`
            rounded-lg border bg-gray-800 px-3 py-2 text-sm text-white
            placeholder:text-gray-500 outline-none transition
            focus:ring-2 focus:ring-brand-500 focus:border-transparent
            ${error ? 'border-red-500' : 'border-gray-700'}
            ${props.disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        />
        {hint && !error && (
          <p className="text-xs text-gray-500">{hint}</p>
        )}
        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}
      </div>
    )
  }
)

FormField.displayName = 'FormField'
