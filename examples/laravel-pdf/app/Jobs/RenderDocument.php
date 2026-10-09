<?php
namespace App\Jobs;

use App\Models\Document;
use App\Support\Invoice;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Queue\Middleware\WithoutOverlapping;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Process;
use Illuminate\Support\Str;
use Throwable;

class RenderDocument implements ShouldQueue
{
    use Queueable;
    public int $tries = 3;
    public int $timeout = 45;
    public bool $failOnTimeout = true;

    public function __construct(public string $documentId) {}
    public function backoff(): array { return [2, 10]; }
    public function middleware(): array
    {
        return [(new WithoutOverlapping($this->documentId))->expireAfter(90)->releaseAfter(2)];
    }

    public function handle(): void
    {
        $document = Document::find($this->documentId);
        if (!$document || $document->expires_at->isPast() || ($document->state === 'ready' && is_file($document->pdfPath()))) {
            return;
        }
        $document->update(['state' => 'processing', 'attempts' => $this->attempts(), 'error' => null]);
        $temporary = null;
        try {
            $html = view('invoice', Invoice::viewData($document->payload))->render();
            $result = Process::path(base_path())->timeout(30)
                ->input(json_encode(['html' => $html, 'title' => 'Invoice '.$document->payload['number']], JSON_THROW_ON_ERROR))
                ->run([config('pdf.python'), '-I', base_path('renderer/render.py')]);
            $pdf = $result->output();
            if (!$result->successful() || !str_starts_with($pdf, '%PDF-') || strlen($pdf) > 4000000) {
                throw new \RuntimeException('Renderer did not produce a bounded PDF.');
            }
            File::ensureDirectoryExists(dirname($document->pdfPath()), 0700);
            $temporary = $document->pdfPath().'.'.Str::uuid().'.tmp';
            if (file_put_contents($temporary, $pdf, LOCK_EX) !== strlen($pdf)) {
                throw new \RuntimeException('PDF write failed.');
            }
            @chmod($temporary, 0600);
            DB::transaction(function () use ($temporary, $document) {
                // Obtain a write lock before the file promotion. Pruning uses the same DB.
                $alive = Document::whereKey($document->id)->where('expires_at', '>', now())->update(['state' => 'processing']);
                if (!$alive) { return; }
                if (!rename($temporary, $document->pdfPath())) { throw new \RuntimeException('PDF promotion failed.'); }
                Document::whereKey($document->id)->update(['state' => 'ready', 'error' => null]);
            }, 3);
        } catch (Throwable) {
            Document::whereKey($this->documentId)->where('state', '!=', 'ready')->update(['state' => 'queued', 'error' => 'render_retry']);
            // Do not put invoice text, raw HTML, subprocess output or credentials in failed_jobs/logs.
            throw new \RuntimeException('PDF render failed; inspect the renderer installation and trusted template.');
        } finally {
            if ($temporary && is_file($temporary)) { unlink($temporary); }
        }
    }

    public function failed(?Throwable $exception): void
    {
        Document::whereKey($this->documentId)->where('state', '!=', 'ready')->update(['state' => 'failed', 'error' => 'render_failed']);
    }
}
