import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://hgzlobvrhtqcheelesvk.supabase.co'
const supabaseKey = 'sb_publishable_GdwHslPqSmYQgW4GISJCsA_4Q5B2NNo'

export const supabase = createClient(supabaseUrl, supabaseKey)