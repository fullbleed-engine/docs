<?php
return [
    'python' => env('FULLBLEED_PYTHON', ''),
    'owners' => ['primary' => env('PDF_API_KEY', ''), 'secondary' => env('PDF_SECONDARY_API_KEY', '')],
    'retention_hours' => max(1, min(168, (int) env('PDF_RETENTION_HOURS', 24))),
];
