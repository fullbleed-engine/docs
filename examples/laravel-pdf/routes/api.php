<?php
use App\Http\Controllers\DocumentController;
use Illuminate\Support\Facades\Route;

Route::post('/documents', [DocumentController::class, 'store'])->middleware('throttle:pdf-submit');
Route::get('/documents/{id}', [DocumentController::class, 'show'])->whereUuid('id')->middleware('throttle:pdf-read');
Route::get('/documents/{id}/download', [DocumentController::class, 'download'])->whereUuid('id')->middleware('throttle:pdf-read');
