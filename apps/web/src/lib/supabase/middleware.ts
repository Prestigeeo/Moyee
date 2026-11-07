import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { SUPABASE_ANON_KEY, SUPABASE_URL, isAuthConfigured } from "@/lib/env";

const AUTH_PAGES = ["/sign-in", "/sign-up"];

/** Refreshes the Supabase session cookie and guards /app routes. */
export async function updateSession(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isAppRoute = pathname === "/app" || pathname.startsWith("/app/");

  if (!isAuthConfigured) {
    return NextResponse.next({ request });
  }

  let response = NextResponse.next({ request });
  const supabase = createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (toSet) => {
        toSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        toSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user && isAppRoute) {
    return redirectTo(request, "/sign-in", pathname);
  }
  if (user && AUTH_PAGES.includes(pathname)) {
    return redirectTo(request, "/app");
  }
  return response;
}

function redirectTo(request: NextRequest, path: string, next?: string) {
  const url = request.nextUrl.clone();
  url.pathname = path;
  url.search = next ? `?next=${encodeURIComponent(next)}` : "";
  return NextResponse.redirect(url);
}
