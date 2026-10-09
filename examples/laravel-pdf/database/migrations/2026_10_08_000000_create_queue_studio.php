<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('documents', function (Blueprint $table) {
            $table->uuid('id')->primary(); $table->string('owner');
            $table->string('request_key', 64); $table->string('payload_hash', 64);
            $table->text('payload'); $table->string('state'); $table->unsignedInteger('attempts')->default(0);
            $table->string('error')->nullable(); $table->timestamp('expires_at')->index(); $table->timestamps();
            $table->unique(['owner', 'request_key']);
        });
        Schema::create('jobs', function (Blueprint $table) {
            $table->id(); $table->string('queue')->index(); $table->longText('payload');
            $table->unsignedTinyInteger('attempts'); $table->unsignedInteger('reserved_at')->nullable();
            $table->unsignedInteger('available_at'); $table->unsignedInteger('created_at');
        });
        Schema::create('failed_jobs', function (Blueprint $table) {
            $table->id(); $table->string('uuid')->unique(); $table->text('connection'); $table->text('queue');
            $table->longText('payload'); $table->longText('exception'); $table->timestamp('failed_at')->useCurrent();
        });
        Schema::create('cache', function (Blueprint $table) {
            $table->string('key')->primary(); $table->mediumText('value'); $table->integer('expiration');
        });
        Schema::create('cache_locks', function (Blueprint $table) {
            $table->string('key')->primary(); $table->string('owner'); $table->integer('expiration');
        });
    }
    public function down(): void
    {
        foreach (['documents', 'jobs', 'failed_jobs', 'cache', 'cache_locks'] as $table) { Schema::dropIfExists($table); }
    }
};
