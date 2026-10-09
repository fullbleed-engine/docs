<?php
// Creates only local configuration. Never replaces an existing .env or database.
$python = isset($argv[1]) && is_file($argv[1])
    ? realpath(dirname($argv[1])).DIRECTORY_SEPARATOR.basename($argv[1])
    : false;
// Preserve the executable symlink: resolving .venv/bin/python to the system
// binary would bypass the virtual environment and its installed packages.
if (!$python || !is_file($python) || preg_match('/[\r\n"]/', $python)) {
    fwrite(STDERR, "Usage: php setup.php /absolute/path/to/venv/python\n");
    exit(1);
}
foreach (['bootstrap/cache', 'database', 'storage/app/private/documents', 'storage/framework/views', 'storage/framework/cache', 'storage/logs'] as $directory) {
    if (!is_dir(__DIR__.'/'.$directory)) { mkdir(__DIR__.'/'.$directory, 0700, true); }
}
if (!is_file(__DIR__.'/.env')) {
    $env = file_get_contents(__DIR__.'/.env.example');
    $env = str_replace("APP_KEY=\n", 'APP_KEY=base64:'.base64_encode(random_bytes(32))."\n", $env);
    $env = str_replace("PDF_API_KEY=\n", 'PDF_API_KEY='.bin2hex(random_bytes(32))."\n", $env);
    $env = str_replace("FULLBLEED_PYTHON=\n", 'FULLBLEED_PYTHON="'.str_replace('\\', '/', $python).'"'."\n", $env);
    file_put_contents(__DIR__.'/.env', $env, LOCK_EX);
    chmod(__DIR__.'/.env', 0600);
}
if (!is_file(__DIR__.'/database/database.sqlite')) {
    touch(__DIR__.'/database/database.sqlite');
    chmod(__DIR__.'/database/database.sqlite', 0600);
}
echo "Local configuration ready. The generated service key is in .env. Run php artisan migrate.\n";
