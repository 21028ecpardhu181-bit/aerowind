import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL =
  import.meta.env.VITE_SUPABASE_URL || 'https://avtkzutofgsjzldkimro.supabase.co';

const SUPABASE_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  import.meta.env.VITE_SUPABASE_SERVICE_ROLE_KEY ||
  import.meta.env.VITE_SUPABASE_JWT_ANON ||
  '';

export const supabase = createClient(
  SUPABASE_URL,
  SUPABASE_KEY || 'placeholder-key'
);

export const isSupabaseConfigured = (): boolean => {
  return Boolean(SUPABASE_KEY && SUPABASE_KEY !== 'placeholder-key');
};

/**
 * Health check to verify live Supabase connectivity.
 */
export async function checkSupabaseConnection(): Promise<{ connected: boolean; latencyMs?: number; error?: string }> {
  const start = Date.now();
  try {
    const { error } = await supabase.from('projects').select('id').limit(1);
    // Even if the table doesn't exist yet, a 404 or PGRST error means the server is reachable and authenticated
    return {
      connected: !error || error.code === 'PGRST116' || error.code === '42P01',
      latencyMs: Date.now() - start,
      error: error?.message,
    };
  } catch (err: any) {
    return {
      connected: false,
      latencyMs: Date.now() - start,
      error: err?.message || 'Unknown network error',
    };
  }
}
