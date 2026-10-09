<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Document extends Model
{
    public $incrementing = false;
    protected $keyType = 'string';
    protected $guarded = [];
    protected $hidden = ['payload', 'payload_hash', 'request_key', 'owner'];
    protected function casts(): array
    {
        return ['payload' => 'encrypted:array', 'expires_at' => 'immutable_datetime'];
    }
    public function pdfPath(): string
    {
        return storage_path('app/private/documents/'.$this->id.'.pdf');
    }
    public function status(): array
    {
        return [
            'id' => $this->id, 'state' => $this->state, 'attempts' => $this->attempts,
            'expires_at' => $this->expires_at->toIso8601String(),
            'status_url' => '/api/documents/'.$this->id,
            'download_url' => $this->state === 'ready' ? '/api/documents/'.$this->id.'/download' : null,
            'error' => $this->error,
        ];
    }
}
