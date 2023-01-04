<?php

namespace App\Helper;

use App\Entity\Member;
use libphonenumber\PhoneNumberFormat;
use PhpOffice\PhpSpreadsheet\IOFactory;
use PhpOffice\PhpSpreadsheet\Worksheet\Worksheet;
use Psr\Log\LoggerInterface;

class MemberXlsImporter implements \Psr\Log\LoggerAwareInterface
{
    public const HEADER_NAME_DIRTY = 'noms';
    public const HEADER_NAME = 'name';
    public const HEADER_ADDRESS_DIRTY = 'adresse';
    public const HEADER_ADDRESS = self::HEADER_ADDRESS_DIRTY;
    public const HEADER_CITY_DIRTY = 'ville';
    public const HEADER_CITY = 'city';
    public const HEADER_EMAIL_DIRTY = 'email';
    public const HEADER_EMAIL = self::HEADER_EMAIL_DIRTY;
    public const HEADER_PHONE_DIRTY = 'téléphone';
    public const HEADER_PHONE = 'phone';

    public const HEADERS_DIRTY = [
        MemberXlsImporter::HEADER_NAME_DIRTY,
        MemberXlsImporter::HEADER_ADDRESS_DIRTY,
        MemberXlsImporter::HEADER_CITY_DIRTY,
        MemberXlsImporter::HEADER_EMAIL_DIRTY,
        MemberXlsImporter::HEADER_PHONE_DIRTY,
    ];
    public const HEADERS_CLEAN = [
        MemberXlsImporter::HEADER_NAME,
        MemberXlsImporter::HEADER_ADDRESS,
        MemberXlsImporter::HEADER_CITY,
        MemberXlsImporter::HEADER_EMAIL,
        MemberXlsImporter::HEADER_PHONE,
    ];

    public function __construct(protected ?LoggerInterface $logger = null)
    {
    }

    private array $expectedHeaders = self::HEADERS_DIRTY;

    /**
     * @return array|Member[]
     *
     * @throws \InvalidArgumentException
     */
    public function parse(string $filename = null): array
    {
        $data = $this->read($filename, false);
        if (empty($data)) {
            return [];
        }

        $data = array_values($data);

        if (!empty($this->expectedHeaders)) {
            if ($diff = array_diff(array_values($this->expectedHeaders), array_values($data[0]))) {
                throw new \InvalidArgumentException(sprintf('Incompatible xlsx headers. Got %s, expect %s. Diff %s', json_encode($data[0], true), json_encode($this->expectedHeaders, true), json_encode($diff, true)));
            }
        }

        $headers = array_shift($data);

        $users = [];
        foreach ($data as &$line) {
            self::trimArray($line);

            foreach ($this->convertToMembers(array_combine(self::HEADERS_CLEAN, $line)) as $user) {
                $users[] = $user;
            }
        }

        $this->logger?->debug(sprintf('%d users imported', count($users)));

        return $users;
    }

    protected function read(string $filename = null): array
    {
        if (null === $filename) {
            $filename = __DIR__.'/../DataFixtures/members_fixtures.xlsx';
        }

        if (!file_exists($filename) || !is_readable($filename)) {
            throw new \InvalidArgumentException(sprintf('Unable to find or read file \'%s\'', $filename));
        }

        try {
            $reader = IOFactory::createReaderForFile($filename);
            $filter = new XlsReadFilter(0, null, range('A', 'E'));
            $reader->setReadFilter($filter);

            /** @var Worksheet */
            $workSheet = $reader->load($filename)->getSheet(0);
            $data = $workSheet->toArray(null, false, false, false);
        } catch (\Exception $exception) {
            throw new \RuntimeException('Unable to parse file', 0, $exception);
        }

        return $data;
    }

    public function setExpectedHeaders(array $expectedHeaders): self
    {
        $this->expectedHeaders = $expectedHeaders;

        return $this;
    }

    private function convertToMembers(array $row): array
    {
        $this->logger?->debug('row: '.print_r($row, true));
        $names = explode(',', $row[self::HEADER_NAME]);
        self::trimArray($names);

        if (empty($names)) {
            return [];
        }

        if (count($names) > 1) {
            $this->logger?->debug(sprintf('%d users in one row', count($names)));
        }

        $members = [];
        foreach ($names as $name) {
            $members[] = $m = new Member();
            list($firstname, $lastname) = self::splitName($name);
            $m->setLastname($firstname);
            $m->setFirstname($lastname);
            $m->setEmail($row[self::HEADER_EMAIL]);
            $m->setAddress($row[self::HEADER_ADDRESS]);
            $m->setCityAndZip($row[self::HEADER_CITY]);
            $m->setPhone($this->formatPhone($row[self::HEADER_PHONE]));
        }

        $parent = array_shift($members);
        $parent->setParent(null);
        foreach ($members as $child) {
            $this->logger?->debug(sprintf('set parents %s - child %s', $parent, $child));
            $child->setParent($parent);
        }
        array_unshift($members, $parent);

        $this->logger?->debug(print_r(array_map(fn (Member $member) => sprintf('#User(%s)', $member->__toString()), $members), true));

        return $members;
    }

    private function formatPhone(?string $number, string $country = 'CH'): ?string
    {
        if ('' === trim((string) $number)) {
            return null;
        }
        try {
            $phoneNumberUtil = \libphonenumber\PhoneNumberUtil::getInstance();
            $phoneNumberObject = $phoneNumberUtil->parse($number, $country);

            return $phoneNumberUtil->format($phoneNumberObject, PhoneNumberFormat::E164);
        } catch (\Throwable $e) {
            $this->logger?->warning(sprintf('Unable to parse phone number %s : %s', $number, $e->getMessage()));

            return null;
        }
    }

    /**
     * Guess the name
     * Return array with firstname, lastname.
     */
    private static function splitName(string $name): array
    {
        $exploded = explode(' ', $name);
        $first = array_shift($exploded);

        return [implode(' ', $exploded), $first];
    }

    private static function trimArray(array &$line): void
    {
        $line = array_map(fn ($s) => null === $s ? null : trim($s), $line);
    }

    /**
     * Sets a logger instance on the object.
     */
    public function setLogger(LoggerInterface $logger): void
    {
        $this->logger = $logger;
    }
}
