/* Lumi's skins: what each one adds to the face, shared by the island and the Settings picker.
 * Coordinates are Lumi's own 60 x 50 box, drawn behind the eyes. Keep clear of the eyes and glasses (x 7-53, y 13-29) and
 * of the "!" at x 54, and stay within y -15 to 57: there's 15px of room under the island.
 * .skin-part follows Lumi's body colour, so ears and tails tint with the listening, speaking and focus moods.
 * Everything is solid: the window's transparency is a colour key, so soft or see-through edges outside the body fringe.
 * Names (colours, labels) live in SKINS in lumi/config.py; shapes in lumi-skins.css. */
const LUMI_SKIN_ART = {
    cat: `<path class="skin-part" d="M8 10 12-7l13 10zM52 10 48-7 35 3z"/>
        <path fill="#F58FA0" d="m12.8 5 1-7 6 4.4zM47.2 5l-1-7-6 4.4z"/>
        <path fill="none" stroke="#7A3E10" stroke-opacity=".38" stroke-width="2" stroke-linecap="round" d="M25 4v5M30 3v6M35 4v5"/>
        <path fill="#F58FA0" d="M27.8 29.4h4.4L30 32z"/>
        <path fill="none" stroke="#8A5A3A" stroke-width="1.3" stroke-linecap="round" d="m2.5 29 8 1.4M2.5 35l8-1.6M57.5 29l-8 1.4M57.5 35l-8-1.6"/>`,
    bunny: `<path class="skin-part" d="M15 9c-3-12-2-24 4-24s7 12 5 22zM37 7c1-9 4-16 10-15 8 2 6 10 1 10-3 0-4 3-4 8z"/>
        <path fill="#F7B6C6" d="M17.5 5C16-4 17-11 19-11s3.2 7 2.7 15zM41 5c1-6 3-10 6-9.5 3 .5 2.5 4 0 4-2.5 0-4 2-4.5 5.5z"/>
        <path fill="#F58FA0" d="M28.2 29.8h3.6L30 31.8z"/>`,
    bear: `<circle class="skin-part" cx="10" cy="4" r="8.5"/><circle class="skin-part" cx="50" cy="4" r="8.5"/>
        <circle fill="#A87E5C" cx="10" cy="4" r="4.2"/><circle fill="#A87E5C" cx="50" cy="4" r="4.2"/>
        <ellipse fill="#EBD8C3" cx="30" cy="35" rx="11" ry="8"/>
        <ellipse fill="#3A2A20" cx="30" cy="30.5" rx="3" ry="2"/>`,
    robot: `<path fill="none" stroke="#6F8496" stroke-width="2.4" stroke-linecap="round" d="M30 0v-9"/>
        <circle fill="#4FD6E0" cx="30" cy="-11" r="3.2"/>
        <rect fill="#8CA2B4" x="-4" y="16" width="6" height="14" rx="2"/><rect fill="#8CA2B4" x="58" y="16" width="6" height="14" rx="2"/>
        <rect fill="#E6EFF6" x="11" y="10" width="38" height="21" rx="8"/>
        <circle fill="#8CA2B4" cx="6" cy="6" r="1.5"/><circle fill="#8CA2B4" cx="54" cy="6" r="1.5"/>
        <circle fill="#8CA2B4" cx="6" cy="44" r="1.5"/><circle fill="#8CA2B4" cx="54" cy="44" r="1.5"/>
        <path fill="none" stroke="#8CA2B4" stroke-width="2" stroke-linecap="round" d="M23 41h14"/>`,
    pixel: `<path fill="#FFFFFF" d="M8 8h12v4H8zM8 12h4v4H8z"/>
        <path fill="#000" fill-opacity=".16" d="M48 34h4v8h-4zM40 42h8v4h-8z"/>
        <path class="skin-part" d="M1-6h4v4H1zM8-11h3v3H8zM50-8h3v3h-3z"/>`,
    hologram: `
        <path fill="none" stroke="#3FBFC0" stroke-width="1.6" stroke-linecap="round" d="M-4 15h6M58 33h6M2 3.5h5M4.5 1v5"/>`,
    cloud: `<g class="skin-part"><circle cx="12" cy="8" r="9"/><circle cx="28" cy="3" r="11"/><circle cx="45" cy="6" r="10"/>
        <circle cx="2" cy="26" r="7"/><circle cx="58" cy="27" r="7"/><circle cx="15" cy="46" r="7"/><circle cx="36" cy="47" r="8"/></g>`,
    slime: `<g class="skin-part"><rect x="8" y="40" width="7" height="17" rx="3.5"/><rect x="33" y="42" width="6" height="12" rx="3"/><rect x="45" y="40" width="5" height="9" rx="2.5"/></g>
        <ellipse fill="#FFFFFF" cx="15" cy="9" rx="6.5" ry="3" transform="rotate(-24 15 9)"/>
        <circle fill="none" stroke="#FFFFFF" stroke-width="1.3" cx="45" cy="37" r="2.5"/>
        <circle fill="#FFFFFF" cx="52" cy="30" r="1.2"/>`,
    sprout: `<path fill="none" stroke="#5FA84E" stroke-width="2.6" stroke-linecap="round" d="M30 3v-9"/>
        <path fill="#7BC463" d="M30-6c-6-8-15-7-17-3 4 6 12 7 17 3z"/>
        <path fill="#5FA84E" d="M30-6c4-7 13-8 16-4-3 6-11 8-16 4z"/>
        <g fill="#CDB98C"><circle cx="9" cy="35" r="1.3"/><circle cx="14" cy="41" r="1.3"/><circle cx="51" cy="35" r="1.3"/><circle cx="46" cy="41" r="1.3"/></g>`,
    santa: `<path fill="#D9423A" d="M9 10C12-6 28-14 42-9c8 3 12 9 13 16h-6c-3-7-5-8-7-6 2 4 4 7 5 9z"/>
        <rect fill="#FFFFFF" x="6" y="5.5" width="44" height="8" rx="4"/>
        <circle fill="#FFFFFF" cx="55" cy="10" r="4.5"/>`,
    pumpkin: `<path fill="none" stroke="#000" stroke-opacity=".16" stroke-width="2" stroke-linecap="round" d="M15 4C6 14 6 36 15 46M45 4c9 10 9 32 0 42M24 1.5c-6 11-6 36 0 47M36 1.5c6 11 6 36 0 47"/>
        <path fill="#6FA34A" d="M26 3c0-5-1-7-3-11l8-1c0 4 2 7 3 12z"/>
        <path fill="none" stroke="#6FA34A" stroke-width="1.8" stroke-linecap="round" d="M33-3c5-4 10-1 7 3"/>`,
    party: `<path fill="#6C8CFF" d="M19 7 33-12l9 17z"/>
        <path fill="#F5B83D" d="M24.5 1.5 37-3l1.5 3-11 4.5zM31-7l3-1 1.3 2.5-5 2z"/>
        <circle fill="#FFFFFF" cx="33" cy="-12" r="3"/>
        <g><rect fill="#6C8CFF" x="6" y="11" width="3.5" height="3.5" rx="1" transform="rotate(20 8 13)"/><rect fill="#F5B83D" x="52" y="10" width="3.5" height="3.5" rx="1" transform="rotate(-15 54 12)"/>
        <rect fill="#34C77B" x="7" y="40" width="3.5" height="3.5" rx="1" transform="rotate(35 9 42)"/><rect fill="#6C8CFF" x="49" y="39" width="3.5" height="3.5" rx="1" transform="rotate(15 51 41)"/>
        <rect fill="#F5B83D" x="20" y="43" width="3.5" height="3.5" rx="1" transform="rotate(-25 22 45)"/><rect fill="#34C77B" x="38" y="44" width="3.5" height="3.5" rx="1" transform="rotate(40 40 46)"/></g>`
};
