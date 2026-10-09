<?php
return [
    'default' => 'database',
    'connections' => ['database' => [
        'driver' => 'database', 'connection' => 'sqlite', 'table' => 'jobs',
        'queue' => 'pdf', 'retry_after' => 120,
        // Same SQLite connection as documents: both inserts commit atomically.
        'after_commit' => false,
    ]],
    'failed' => ['driver' => 'database-uuids', 'database' => 'sqlite', 'table' => 'failed_jobs'],
];
