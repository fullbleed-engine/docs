<?php
namespace App\Http\Controllers;

use App\Jobs\RenderDocument;
use App\Models\Document;
use App\Support\Invoice;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class DocumentController
{
    public function store(Request $request)
    {
        abort_unless(strtolower(explode(';', $request->header('Content-Type', ''))[0]) === 'application/json', 415, 'Use application/json.');
        abort_if(strlen($request->getContent()) > 65536, 413, 'Invoice request is too large.');
        try {
            $input = json_decode($request->getContent(), true, 32, JSON_THROW_ON_ERROR);
        } catch (\JsonException) {
            abort(400, 'Invalid JSON.');
        }
        abort_unless(is_array($input) && !array_is_list($input), 422, 'Expected an invoice object.');
        $data = Invoice::validate($input);
        $key = $request->header('Idempotency-Key', '');
        abort_unless(preg_match('/^[A-Za-z0-9_-]{8,100}$/D', $key) === 1, 422, 'Use an Idempotency-Key of 8 to 100 letters, numbers, underscores or hyphens.');
        $owner = $request->attributes->get('pdf_owner');
        $digest = hash('sha256', json_encode($data, JSON_THROW_ON_ERROR));
        $document = DB::transaction(function () use ($data, $key, $owner, $digest) {
            $existing = Document::where('owner', $owner)->where('request_key', hash('sha256', $key))->first();
            if ($existing) {
                abort_if($existing->expires_at->isPast(), 410, 'Document expired; use a new idempotency key.');
                abort_unless(hash_equals($existing->payload_hash, $digest), 409, 'That idempotency key belongs to different data.');
                return $existing;
            }
            $document = Document::create([
                'id' => (string) Str::uuid(), 'owner' => $owner, 'request_key' => hash('sha256', $key),
                'payload_hash' => $digest, 'payload' => $data, 'state' => 'queued', 'attempts' => 0,
                'expires_at' => now()->addHours(config('pdf.retention_hours')),
            ]);
            // Immediate insert into jobs uses this very same DB transaction.
            Bus::dispatch(new RenderDocument($document->id));
            return $document;
        }, 3);
        return response()->json($document->status(), $document->state === 'ready' ? 200 : 202,
            ['Location' => '/api/documents/'.$document->id, 'Retry-After' => '2']);
    }

    private function owned(Request $request, string $id): Document
    {
        $document = Document::where('owner', $request->attributes->get('pdf_owner'))->findOrFail($id);
        abort_if($document->expires_at->isPast(), 410, 'Document expired.');
        return $document;
    }

    public function show(Request $request, string $id)
    {
        return response()->json($this->owned($request, $id)->status());
    }

    public function download(Request $request, string $id)
    {
        $document = $this->owned($request, $id);
        abort_unless($document->state === 'ready' && is_file($document->pdfPath()), 409, 'PDF is not ready.');
        return response()->download($document->pdfPath(), $id.'.pdf', ['Content-Type' => 'application/pdf']);
    }
}
