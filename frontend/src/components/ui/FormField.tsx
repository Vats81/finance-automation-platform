"use client";

import { Children, ReactElement, cloneElement, isValidElement, useId } from "react";

type ControlProps = { id?: string; "aria-invalid"?: boolean; "aria-describedby"?: string };

/**
 * A labelled form control. The label used to be a bare <label> sitting next
 * to the input with nothing connecting them, so every field in the app had
 * no accessible name — a screen reader announced an unnamed text box, and
 * clicking the label didn't focus the field. A QA pass found it on the login
 * form; it affected every form.
 *
 * Now the label is tied to its control with htmlFor/id, and an error message
 * is linked via aria-describedby (with aria-invalid) so it's announced with
 * the field. This works for the usual case of a single control child
 * (<Input>, <Select>, <input>); any other children render as before, just
 * without the association. A control's own `id` is respected if it has one.
 */
export function FormField({
  label,
  error,
  children,
}: {
  label: string;
  error?: string | null;
  children: React.ReactNode;
}) {
  const generatedId = useId();
  const errorId = `${generatedId}-error`;

  const only = Children.count(children) === 1 && isValidElement(children) ? children : null;
  const control = only as ReactElement<ControlProps> | null;
  const controlId = control ? (control.props.id ?? generatedId) : undefined;

  return (
    <div>
      <label htmlFor={controlId} className="mb-1 block text-sm font-medium">
        {label}
      </label>
      {control
        ? cloneElement(control, {
            id: controlId,
            ...(error ? { "aria-invalid": true, "aria-describedby": errorId } : {}),
          })
        : children}
      {error && (
        <p id={errorId} role="alert" className="mt-1 text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
