<?php
namespace App\Support;

use Illuminate\Support\Facades\Validator;

class Invoice
{
    public static function validate(array $data): array
    {
        $text = ['required', 'string', 'regex:/^[^\x00-\x1F\x7F]+$/u'];
        $integer = fn ($attribute, $value, $fail) => is_int($value) ?: $fail('Quantity must be a JSON integer.');
        $price = fn ($attribute, $value, $fail) => is_string($value) ?: $fail('Use a decimal string for prices.');
        $v = Validator::make(['invoice' => $data], [
            'invoice' => ['required', 'array:number,customer,issued,due,items'],
            'invoice.number' => ['required', 'string', 'regex:/^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$/D'],
            'invoice.customer' => [...$text, 'max:80'],
            'invoice.issued' => ['required', 'date_format:Y-m-d'],
            'invoice.due' => ['required', 'date_format:Y-m-d', 'after_or_equal:invoice.issued'],
            'invoice.items' => ['required', 'array', 'list', 'min:1', 'max:100'],
            'invoice.items.*' => ['required', 'array:description,quantity,unit_price'],
            'invoice.items.*.description' => [...$text, 'max:160'],
            'invoice.items.*.quantity' => ['required', 'integer', 'min:1', 'max:100', $integer],
            'invoice.items.*.unit_price' => ['required', 'string', 'regex:/^(0|[1-9][0-9]{0,5})\.[0-9]{2}$/D', $price],
        ])->validate()['invoice'];
        // Canonical field order makes idempotency independent of JSON object-key order.
        return [
            'number' => $v['number'], 'customer' => $v['customer'], 'issued' => $v['issued'], 'due' => $v['due'],
            'items' => array_map(fn ($i) => ['description' => $i['description'], 'quantity' => $i['quantity'], 'unit_price' => $i['unit_price']], $v['items']),
        ];
    }

    public static function viewData(array $invoice): array
    {
        $total = 0;
        foreach ($invoice['items'] as &$item) {
            [$whole, $fraction] = explode('.', $item['unit_price']);
            $cents = ((int) $whole * 100 + (int) $fraction) * $item['quantity'];
            $total += $cents;
            $item['amount'] = self::money($cents);
        }
        unset($item);
        return ['invoice' => $invoice, 'total' => self::money($total)];
    }

    private static function money(int $cents): string
    {
        return number_format(intdiv($cents, 100), 0, '.', ',').'.'.str_pad((string) ($cents % 100), 2, '0', STR_PAD_LEFT);
    }
}
