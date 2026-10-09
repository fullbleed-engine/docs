<?php
return ['default' => 'database', 'stores' => ['database' => [
    'driver' => 'database', 'connection' => 'sqlite', 'table' => 'cache',
    'lock_connection' => 'sqlite', 'lock_table' => 'cache_locks',
]], 'prefix' => 'fullbleed_queue_'];
