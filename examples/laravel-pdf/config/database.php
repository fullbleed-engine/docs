<?php
return [
    'default' => 'sqlite',
    'connections' => ['sqlite' => [
        'driver' => 'sqlite', 'database' => database_path('database.sqlite'), 'prefix' => '',
        'foreign_key_constraints' => true, 'busy_timeout' => 5000,
        'journal_mode' => 'WAL', 'synchronous' => 'NORMAL',
        'transaction_mode' => 'IMMEDIATE',
    ]],
    'migrations' => ['table' => 'migrations', 'update_date_on_publish' => true],
];
