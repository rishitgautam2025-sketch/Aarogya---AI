import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://hgzlobvrhtqcheelesvk.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhnemxvYnZyaHRxY2hlZWxlc3ZrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAxMTE4MzMsImV4cCI6MjA5NTY4NzgzM30.IEo7fF1HgL68ihIb4Kjwerf6SIqzAj4LPsfHOM9PiIw';

export const supabase = createClient(supabaseUrl, supabaseKey)