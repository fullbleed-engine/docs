<?php
namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class ServiceKey
{
    public function handle(Request $request, Closure $next)
    {
        $token = $request->bearerToken();
        $owner = null;
        foreach (config('pdf.owners') as $name => $key) {
            if (is_string($key) && strlen($key) >= 32 && is_string($token) && hash_equals($key, $token)) {
                $owner = $name;
                break;
            }
        }
        if ($owner === null) {
            return response()->json(['message' => 'A valid service key is required.'], 401,
                ['Cache-Control' => 'private, no-store', 'WWW-Authenticate' => 'Bearer']);
        }
        $request->attributes->set('pdf_owner', $owner);
        $response = $next($request);
        $response->headers->set('Cache-Control', 'private, no-store');
        $response->headers->set('X-Content-Type-Options', 'nosniff');
        return $response;
    }
}
