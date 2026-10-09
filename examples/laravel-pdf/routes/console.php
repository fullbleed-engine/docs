<?php
use App\Models\Document;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schedule;

Artisan::command('documents:prune', function () {
    $removed = 0;
    Document::where('expires_at', '<=', now())->select('id')->chunkById(100, function ($documents) use (&$removed) {
        foreach ($documents as $candidate) {
            DB::transaction(function () use ($candidate, &$removed) {
                $document = Document::find($candidate->id);
                if (!$document || $document->expires_at->isFuture()) { return; }
                $document->delete();
                if (is_file($document->pdfPath()) && !unlink($document->pdfPath())) {
                    throw new RuntimeException('Unable to delete expired PDF.');
                }
                $removed++;
            }, 3);
        }
    });
    foreach (glob(storage_path('app/private/documents/*.tmp')) ?: [] as $temporary) {
        if (filemtime($temporary) < time() - 7200) { unlink($temporary); }
    }
    $this->info('Removed '.$removed.' expired documents.');
})->purpose('Delete expired invoice inputs and private PDFs');

Schedule::command('documents:prune')->everyFiveMinutes()->withoutOverlapping();
Schedule::command('queue:prune-failed --hours=24')->daily();
