<?php

$_SERVER['HTTP_X_FORWARDED_PROTO'] = $_SERVER['HTTP_CUSTOM_FORWARDED_PROTO'] ?? $_SERVER['HTTP_X_FORWARDED_PROTO'] ?? 'http';
$_SERVER['HTTP_X_FORWARDED_PORT'] = $_SERVER['HTTP_CUSTOM_FORWARDED_PORT'] ?? $_SERVER['HTTP_X_FORWARDED_PORT'] ?? '80';

use App\Kernel;

require_once dirname(__DIR__).'/vendor/autoload_runtime.php';

return fn (array $context) => new Kernel($context['APP_ENV'], (bool) $context['APP_DEBUG']);
