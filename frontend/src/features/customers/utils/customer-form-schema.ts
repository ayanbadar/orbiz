import { z } from "zod";

/** The one customer form schema — used by the create/edit page and the order-form dialog. */
export const customerFormSchema = z.object({
  name: z.string().trim().min(1, "Enter a customer name."),
  email: z
    .string()
    .trim()
    .refine(
      (value) => value === "" || z.email().safeParse(value).success,
      "Enter a valid email address.",
    ),
  phone: z.string().trim().max(64, "Keep the phone number under 64 characters."),
  notes: z.string().trim(),
});

export type CustomerFormValues = z.infer<typeof customerFormSchema>;

export const EMPTY_CUSTOMER_FORM: CustomerFormValues = {
  name: "",
  email: "",
  phone: "",
  notes: "",
};
