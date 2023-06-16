<?php

namespace App\Helper;

use App\Entity\Member;
use App\Entity\ParseResult;
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
    public const HEADER_PARENT = 'parent';
    public const HEADER_SUBSCRIPTION_TYPE = 'sympatisant';

    public const HEADERS_DIRTY = [
        MemberXlsImporter::HEADER_NAME_DIRTY,
        MemberXlsImporter::HEADER_ADDRESS_DIRTY,
        MemberXlsImporter::HEADER_CITY_DIRTY,
        MemberXlsImporter::HEADER_EMAIL_DIRTY,
        MemberXlsImporter::HEADER_PHONE_DIRTY,
        MemberXlsImporter::HEADER_PARENT,
        MemberXlsImporter::HEADER_SUBSCRIPTION_TYPE,
    ];
    public const HEADERS_CLEAN = [
        MemberXlsImporter::HEADER_NAME,
        MemberXlsImporter::HEADER_ADDRESS,
        MemberXlsImporter::HEADER_CITY,
        MemberXlsImporter::HEADER_EMAIL,
        MemberXlsImporter::HEADER_PHONE,
        MemberXlsImporter::HEADER_PARENT,
        MemberXlsImporter::HEADER_SUBSCRIPTION_TYPE,
    ];

    public function __construct(protected AddressConverterService $addressConverterService, protected ?LoggerInterface $logger = null)
    {
    }

    private array $expectedHeaders = self::HEADERS_DIRTY;

    /**
     * @return ParseResult<Member>
     *
     * @throws \InvalidArgumentException
     */
    public function parse(string $filename): ParseResult
    {
        $data = $this->read($filename);
        if (empty($data)) {
            return new ParseResult([]);
        }

        $data = array_values($data);

        if (!empty($this->expectedHeaders)) {
            if ($diff = array_diff(array_values($this->expectedHeaders), array_values($data[0]))) {
                throw new \InvalidArgumentException(sprintf('Incompatible xlsx headers. Got %s, expect %s. Diff %s', json_encode($data[0], true), json_encode($this->expectedHeaders, true), json_encode($diff, true)));
            }
        }

        $headers = array_shift($data);

        $users = [];
        $extras = [];
        foreach ($data as &$line) {
            self::trimArray($line);

            foreach ($this->convertToMembers(array_combine(self::HEADERS_CLEAN, $line), $extras) as $user) {
                $users[] = $user;
            }
        }

        // We read the parent column and assign the right member to it.
        $this->fixParents($users, array_map(function (array $extra) { return $extra[self::HEADER_PARENT]; }, $extras));

        $this->logger?->debug(sprintf('%d users imported', count($users)));

        return new ParseResult($users, $extras);
    }

    protected function read(string $filename): array
    {
        if (!file_exists($filename) || !is_readable($filename)) {
            throw new \InvalidArgumentException(sprintf('Unable to find or read file \'%s\'', $filename));
        }

        try {
            $reader = IOFactory::createReaderForFile($filename);
            $filter = new XlsReadFilter(0, null, range('A', 'G'));
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

    private function convertToMembers(array $row, array &$extra): array
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
            $m->setLastname($lastname);
            $m->setFirstname($firstname);
            $m->setEmail($row[self::HEADER_EMAIL]);
            list($address, $addressNumber) = $this->addressConverterService->split($row[self::HEADER_ADDRESS]);

            $m->setAddress($address);
            $m->setAddressNumber($addressNumber);
            $m->setCityAndZip($row[self::HEADER_CITY]);
            $m->setPhone($this->formatPhone($row[self::HEADER_PHONE]));
            // The parent columns contains the fullname of the parent user.
            // We store an array indexed by member hash, with the value of the column.
            $extra[spl_object_hash($m)][self::HEADER_PARENT] = $row[self::HEADER_PARENT];
            $extra[spl_object_hash($m)][self::HEADER_SUBSCRIPTION_TYPE] = $row[self::HEADER_SUBSCRIPTION_TYPE];
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
        $temp = array_merge([], $exploded);
        $firstname = array_pop($temp);

        return 1 == count($exploded) ? [$firstname, null] : [$firstname, implode(' ', $temp)];
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

    private function fixParents(array $users, array $parents): void
    {
        // Hash all the imported user in array index
        $parentListHash = array_map('spl_object_hash', $users);
        $parentsByHash = array_combine($parentListHash, $users);
        unset($parentListHash);
        // Keep only the column with a parent defined
        $parents = array_filter($parents);

        // Search the user to assign the parent to it.
        foreach ($parents as $hash => $parentName) {
            if (!isset($parentsByHash[$hash])) {
                throw new \RuntimeException('Invalid parent detection');
            }

            /** @var Member $user */
            $user = $parentsByHash[$hash];
            // Find the parent by fullName and assign it to the corresponding user.
            /** @var Member|null $parent */
            $parent = $this->searchImportedUserByName($parentName, $users);
            $parentName = $parent?->getFullName();
            $userName = $user->getFullname();

            $this->logger?->debug($parent ? "Parent found $parentName -> $userName" : "Parent not found $parentName");
            $user->setParent($parent);
        }
    }

    private function searchImportedUserByName(?string $parentName, array $importedUsers): ?Member
    {
        if (null === $parentName) {
            return null;
        }

        /** @var Member $user */
        foreach ($importedUsers as $user) {
            // Match by firstname lastname
            if ($user->getFullname() === $parentName) {
                return $user;
            }
            // Match by lastname firstname
            if (implode(' ', [$user->getLastname(), $user->getFirstname()]) === $parentName) {
                return $user;
            }
        }

        return null;
    }
}
