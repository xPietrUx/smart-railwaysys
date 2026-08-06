export const load = ({ cookies }) => ({
	authenticated: Boolean(cookies.get('srs_session') || cookies.get('srs_guest'))
});
