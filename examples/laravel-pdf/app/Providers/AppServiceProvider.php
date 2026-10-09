<?php
namespace App\Providers;

use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function boot(): void
    {
        RateLimiter::for('pdf-submit', fn (Request $r) => Limit::perMinute(30)->by($r->attributes->get('pdf_owner')));
        RateLimiter::for('pdf-read', fn (Request $r) => Limit::perMinute(300)->by($r->attributes->get('pdf_owner')));
    }
}
